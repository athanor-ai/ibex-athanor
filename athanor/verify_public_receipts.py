#!/usr/bin/env python3
"""Verify public Ibex receipt manifests and selected-toolchain policy."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
POLICY_PATH = ROOT / "toolchain_policy.json"
FRONTIER_ROOT = ROOT / "ppa_frontier"
PUBLIC_TEXT_PATHS = [
    ROOT.parent / "README.md",
    ROOT / "README.md",
    FRONTIER_ROOT / "README.md",
]


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"{path}: expected JSON object")
    return data


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_json(data: Any) -> str:
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _sha256_vcd_normalized(path: Path) -> str:
    """Hash VCD content with nondeterministic Icarus `$date` metadata removed."""
    digest = hashlib.sha256()
    skipping_date = False
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped.startswith("$date"):
                skipping_date = True
            if not skipping_date:
                digest.update(line.encode())
            if skipping_date and stripped.endswith("$end"):
                skipping_date = False
    return digest.hexdigest()


def _verify_manifest_hashes(manifest_path: Path, manifest: dict[str, Any]) -> None:
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict) or not artifacts:
        raise SystemExit(f"{manifest_path}: missing artifacts map")
    module_dir = manifest_path.parent
    for artifact_name, artifact_ref in artifacts.items():
        if not isinstance(artifact_ref, dict):
            raise SystemExit(
                f"{manifest_path}: artifact {artifact_name} must be an object"
            )
        rel_path = artifact_ref.get("path")
        expected_sha = artifact_ref.get("sha256")
        if not isinstance(rel_path, str) or not isinstance(expected_sha, str):
            raise SystemExit(
                f"{manifest_path}: artifact {artifact_name} missing path or sha256"
            )
        artifact_path = module_dir / rel_path
        if not artifact_path.is_file():
            raise SystemExit(f"{manifest_path}: artifact {rel_path} does not exist")
        actual_sha = _sha256(artifact_path)
        if actual_sha != expected_sha:
            raise SystemExit(
                f"{manifest_path}: artifact {rel_path} sha256 mismatch "
                f"(expected {expected_sha}, got {actual_sha})"
            )


def _lookup_path(data: Any, dotted_path: str) -> Any:
    current = data
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(dotted_path)
        current = current[part]
    return current


def _load_row_contracts(policy: dict[str, Any]) -> dict[str, dict[str, Any]]:
    contracts = policy.get("row_contracts")
    if not isinstance(contracts, dict) or not contracts:
        raise SystemExit(f"{POLICY_PATH}: missing row_contracts registry")
    expected_sha = policy.get("row_contracts_sha256")
    actual_sha = _sha256_json(contracts)
    if expected_sha != actual_sha:
        raise SystemExit(
            f"{POLICY_PATH}: row_contracts registry sha256 mismatch "
            f"(expected {expected_sha}, got {actual_sha})"
        )
    for name, contract in contracts.items():
        if not isinstance(name, str) or not name:
            raise SystemExit(f"{POLICY_PATH}: row_contract names must be non-empty")
        if not isinstance(contract, dict):
            raise SystemExit(f"{POLICY_PATH}: row_contract {name!r} must be an object")
        if not isinstance(contract.get("required_policy"), dict):
            raise SystemExit(
                f"{POLICY_PATH}: row_contract {name!r} missing required_policy"
            )
        required_receipts = contract.get("required_receipts")
        if not isinstance(required_receipts, list) or not all(
            isinstance(item, str) and item for item in required_receipts
        ):
            raise SystemExit(
                f"{POLICY_PATH}: row_contract {name!r} missing required_receipts"
            )
        assertions = contract.get("assertions")
        if not isinstance(assertions, list):
            raise SystemExit(f"{POLICY_PATH}: row_contract {name!r} missing assertions")
    return contracts


def _verify_manifest_contract(
    manifest_path: Path,
    manifest: dict[str, Any],
    row_contracts: dict[str, dict[str, Any]],
) -> str:
    module = manifest.get("module")
    if not isinstance(module, str) or not module:
        raise SystemExit(f"{manifest_path}: missing public module name")
    contract_name = manifest.get("row_contract")
    if not isinstance(contract_name, str) or not contract_name:
        raise SystemExit(f"{manifest_path}: missing row_contract")
    contract = row_contracts.get(contract_name)
    if contract is None:
        raise SystemExit(
            f"{manifest_path}: row_contract {contract_name!r} is not in the pinned "
            "toolchain policy registry"
        )
    policy = manifest.get("toolchain_policy")
    if not isinstance(policy, dict):
        raise SystemExit(f"{manifest_path}: missing toolchain_policy")
    for key, expected in contract["required_policy"].items():
        if policy.get(key) != expected:
            raise SystemExit(
                f"{manifest_path}: row_contract {contract_name!r} requires "
                f"toolchain_policy.{key}={expected!r}, got {policy.get(key)!r}"
            )

    receipts: dict[str, dict[str, Any]] = {}
    for receipt_name in contract["required_receipts"]:
        receipt_path = manifest_path.parent / receipt_name
        if not receipt_path.is_file():
            raise SystemExit(
                f"{manifest_path}: row_contract {contract_name!r} requires "
                f"receipt {receipt_name!r}"
            )
        receipts[receipt_name] = _load_json(receipt_path)

    for assertion in contract["assertions"]:
        if not isinstance(assertion, dict):
            raise SystemExit(
                f"{POLICY_PATH}: row_contract {contract_name!r} assertion must be an object"
            )
        receipt_name = assertion.get("receipt")
        if not isinstance(receipt_name, str) or receipt_name not in receipts:
            raise SystemExit(
                f"{POLICY_PATH}: row_contract {contract_name!r} assertion references "
                f"unknown receipt {receipt_name!r}"
            )
        receipt = receipts[receipt_name]
        if "equals" in assertion:
            path = assertion.get("path")
            if not isinstance(path, str):
                raise SystemExit(
                    f"{POLICY_PATH}: row_contract {contract_name!r} equality assertion "
                    "missing path"
                )
            try:
                actual = _lookup_path(receipt, path)
            except KeyError:
                raise SystemExit(
                    f"{manifest_path}: receipt {receipt_name!r} missing assertion path {path!r}"
                ) from None
            if actual != assertion["equals"]:
                raise SystemExit(
                    f"{manifest_path}: receipt {receipt_name!r} path {path!r} "
                    f"expected {assertion['equals']!r}, got {actual!r}"
                )
        elif "compare" in assertion:
            compare = assertion["compare"]
            if (
                not isinstance(compare, list)
                or len(compare) != 3
                or compare[1] != ">"
                or not all(isinstance(item, str) for item in compare)
            ):
                raise SystemExit(
                    f"{POLICY_PATH}: row_contract {contract_name!r} has invalid compare assertion"
                )
            left_path, _, right_path = compare
            try:
                left = float(_lookup_path(receipt, left_path))
                right = float(_lookup_path(receipt, right_path))
            except (KeyError, TypeError, ValueError):
                raise SystemExit(
                    f"{manifest_path}: receipt {receipt_name!r} cannot evaluate "
                    f"compare assertion {compare!r}"
                ) from None
            if not left > right:
                raise SystemExit(
                    f"{manifest_path}: receipt {receipt_name!r} expected "
                    f"{left_path} > {right_path}, got {left} <= {right}"
                )
        else:
            raise SystemExit(
                f"{POLICY_PATH}: row_contract {contract_name!r} assertion must use "
                "equals or compare"
            )
    return module


def _verify_toggle_receipt(receipt_path: Path, policy: dict[str, Any]) -> None:
    """ATH-2590: toggle evidence is only valid under the pinned convention.

    Any toggle receipt participating in a public/accepted row must carry the
    selected convention id, the sha256 of the policy's convention block, and
    hash-pinned trace/VCD evidence. Unlabeled or scratch toggle numbers can
    never satisfy an accepted-win receipt.
    """
    conv = policy.get("selected_toggle_convention")
    if not isinstance(conv, dict):
        raise SystemExit(f"{POLICY_PATH}: missing selected_toggle_convention")
    expected_sha = hashlib.sha256(
        json.dumps(conv, indent=4, sort_keys=True).encode()
    ).hexdigest()
    receipt = _load_json(receipt_path)
    if receipt.get("convention_id") != conv.get("id"):
        raise SystemExit(
            f"{receipt_path}: toggle receipt convention_id "
            f"{receipt.get('convention_id')!r} does not match the pinned "
            f"convention {conv.get('id')!r} — unlabeled/scratch toggle evidence rejected"
        )
    if receipt.get("convention_sha256") != expected_sha:
        raise SystemExit(
            f"{receipt_path}: convention_sha256 does not match the policy block — "
            "the receipt was generated under a different (or edited) convention"
        )
    for field in (
        "trace_sha256",
        "vcd_sha256",
        "normalized_vcd_sha256",
        "gold_sha256",
        "gate_sha256",
    ):
        value = receipt.get(field)
        if not isinstance(value, str) or len(value) != 64:
            raise SystemExit(
                f"{receipt_path}: toggle receipt missing hash-pinned {field}"
            )
    if (
        receipt.get("no_x_or_z_on_primary_inputs")
        != "construction_guaranteed_binary_assignments"
    ):
        raise SystemExit(
            f"{receipt_path}: toggle receipt missing no_x_or_z_on_primary_inputs "
            "construction guarantee"
        )
    for name_field, hash_field in (("trace", "trace_sha256"), ("vcd", "vcd_sha256")):
        rel = receipt.get(name_field)
        if not isinstance(rel, str) or not rel:
            raise SystemExit(
                f"{receipt_path}: toggle receipt missing {name_field} file reference"
            )
        candidate = receipt_path.parent / rel
        if not candidate.is_file():
            raise SystemExit(
                f"{receipt_path}: {name_field} file {rel!r} does not exist"
            )
        if _sha256(candidate) != receipt[hash_field]:
            raise SystemExit(
                f"{receipt_path}: {name_field} file does not match {hash_field}"
            )
        if (
            name_field == "vcd"
            and _sha256_vcd_normalized(candidate) != receipt["normalized_vcd_sha256"]
        ):
            raise SystemExit(
                f"{receipt_path}: vcd file does not match normalized_vcd_sha256"
            )


def _selftest_toggle_gate() -> None:
    """Contract test: a conforming receipt passes; unlabeled, wrong-convention,
    and unpinned receipts are rejected. Runs against synthetic fixtures in a
    temp dir so it can execute anywhere (CI-wireable)."""
    import tempfile

    policy = _load_json(POLICY_PATH)
    conv = policy["selected_toggle_convention"]
    conv_sha = hashlib.sha256(
        json.dumps(conv, indent=4, sort_keys=True).encode()
    ).hexdigest()
    trace_bytes = b'{"cycle": 0}\n'
    vcd_text = "$date\n  selftest\n$end\n$version\n  test\n$end\n"
    good = {
        "convention_id": conv["id"],
        "convention_sha256": conv_sha,
        "trace": "toggle_trace.json",
        "trace_sha256": hashlib.sha256(trace_bytes).hexdigest(),
        "vcd": "toggle.vcd",
        "vcd_sha256": hashlib.sha256(vcd_text.encode()).hexdigest(),
        "normalized_vcd_sha256": hashlib.sha256(
            "$version\n  test\n$end\n".encode()
        ).hexdigest(),
        "gold_sha256": "2" * 64,
        "gate_sha256": "3" * 64,
        "no_x_or_z_on_primary_inputs": "construction_guaranteed_binary_assignments",
    }
    cases = [
        ("conforming", good, True),
        ("unlabeled", {k: v for k, v in good.items() if k != "convention_id"}, False),
        ("wrong_convention", {**good, "convention_id": "scratch_trace_v0"}, False),
        ("edited_convention", {**good, "convention_sha256": "f" * 64}, False),
        ("missing_trace_ref", {k: v for k, v in good.items() if k != "trace"}, False),
        ("missing_vcd_ref", {k: v for k, v in good.items() if k != "vcd"}, False),
        ("unpinned_vcd", {k: v for k, v in good.items() if k != "vcd_sha256"}, False),
        (
            "unpinned_normalized_vcd",
            {k: v for k, v in good.items() if k != "normalized_vcd_sha256"},
            False,
        ),
        (
            "missing_no_x_guarantee",
            {k: v for k, v in good.items() if k != "no_x_or_z_on_primary_inputs"},
            False,
        ),
    ]
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        (tmp / "toggle_trace.json").write_bytes(trace_bytes)
        (tmp / "toggle.vcd").write_text(vcd_text)
        for name, receipt, should_pass in cases:
            rp = tmp / f"{name}.json"
            rp.write_text(json.dumps(receipt))
            try:
                _verify_toggle_receipt(rp, policy)
                outcome = True
            except SystemExit:
                outcome = False
            if outcome != should_pass:
                raise SystemExit(
                    f"selftest case {name!r}: expected pass={should_pass}, got {outcome}"
                )
        for missing_name in ("missing_trace_file", "missing_vcd_file"):
            tmp_missing = tmp / missing_name
            tmp_missing.mkdir()
            (tmp_missing / "toggle_trace.json").write_bytes(trace_bytes)
            (tmp_missing / "toggle.vcd").write_text(vcd_text)
            if missing_name == "missing_trace_file":
                (tmp_missing / "toggle_trace.json").unlink()
            else:
                (tmp_missing / "toggle.vcd").unlink()
            rp = tmp_missing / "receipt.json"
            rp.write_text(json.dumps(good))
            try:
                _verify_toggle_receipt(rp, policy)
            except SystemExit:
                continue
            raise SystemExit(
                f"selftest case {missing_name!r}: expected pass=False, got True"
            )
    total_cases = len(cases) + 2
    print(f"toggle-gate selftest: {total_cases}/{total_cases} cases behave as required")


def _selftest_contract_gate() -> None:
    policy = _load_json(POLICY_PATH)
    contracts = _load_row_contracts(policy)
    manifest_path = FRONTIER_ROOT / "ibex_alu_bwlogic" / "manifest.json"
    manifest = _load_json(manifest_path)

    def with_temp_files(
        manifest_update: dict[str, Any] | None = None,
        receipt_update: dict[str, Any] | None = None,
        remove_receipt: str | None = None,
    ) -> tuple[Path, dict[str, Any]]:
        tmp = Path(tempfile.mkdtemp())
        module_dir = tmp / "ibex_alu_bwlogic"
        module_dir.mkdir()
        candidate_manifest = json.loads(json.dumps(manifest))
        if manifest_update:
            candidate_manifest.update(manifest_update)
        for receipt_name in ("area_yosys66.json", "toggle_timing_yosys66.json"):
            if receipt_name == remove_receipt:
                continue
            receipt = _load_json(manifest_path.parent / receipt_name)
            if receipt_name == "toggle_timing_yosys66.json" and receipt_update:
                receipt = json.loads(json.dumps(receipt))
                current = receipt
                for key in ("propagation_delay",):
                    current = current.setdefault(key, {})
                current.update(receipt_update)
            (module_dir / receipt_name).write_text(json.dumps(receipt))
        return module_dir / "manifest.json", candidate_manifest

    cases = [
        ("declared_contract", {}, None, None, contracts, True),
        ("missing_row_contract", {"row_contract": None}, None, None, contracts, False),
        (
            "unknown_row_contract",
            {"row_contract": "unknown_contract"},
            None,
            None,
            contracts,
            False,
        ),
        (
            "assertion_violated",
            {},
            {"status": "improvement"},
            None,
            contracts,
            False,
        ),
        ("missing_receipt", {}, None, "toggle_timing_yosys66.json", contracts, False),
        (
            "edited_registry",
            {},
            None,
            None,
            {
                **contracts,
                "area_tradeoff_yosys66": {
                    **contracts["area_tradeoff_yosys66"],
                    "assertions": [],
                },
            },
            False,
        ),
    ]
    for (
        name,
        manifest_update,
        receipt_update,
        remove_receipt,
        candidate_contracts,
        should_pass,
    ) in cases:
        try:
            candidate_manifest_path, candidate_manifest = with_temp_files(
                manifest_update, receipt_update, remove_receipt
            )
            if name == "edited_registry":
                policy_candidate = {**policy, "row_contracts": candidate_contracts}
                _load_row_contracts(policy_candidate)
            else:
                _verify_manifest_contract(
                    candidate_manifest_path, candidate_manifest, candidate_contracts
                )
            outcome = True
        except SystemExit:
            outcome = False
        if outcome != should_pass:
            raise SystemExit(
                f"contract selftest {name!r}: expected pass={should_pass}, got {outcome}"
            )
    print(f"contract-gate selftest: {len(cases)}/{len(cases)} cases behave as required")


def _verify_public_text() -> None:
    forbidden = [
        "/work" + "dir",
        "kai" + "ros",
        "supa" + "base",
        "Sla" + "ck",
    ]
    for path in PUBLIC_TEXT_PATHS:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            if token in text:
                raise SystemExit(
                    f"{path}: public text contains internal token {token!r}"
                )


def main() -> int:
    if "--selftest" in sys.argv:
        _selftest_toggle_gate()
        _selftest_contract_gate()
        return 0
    policy = _load_json(POLICY_PATH)
    selected = policy.get("selected_toolchain")
    if not isinstance(selected, dict):
        raise SystemExit(f"{POLICY_PATH}: missing selected_toolchain")
    selected_toolchain_id = selected.get("id")
    if selected_toolchain_id != "yosys_0_66_181_oss_cad_suite_2026_06_30":
        raise SystemExit(f"{POLICY_PATH}: selected toolchain must be Yosys 0.66+181")
    row_contracts = _load_row_contracts(policy)

    manifests = sorted(FRONTIER_ROOT.glob("*/manifest.json"))
    if not manifests:
        raise SystemExit(f"{FRONTIER_ROOT}: no module manifests found")

    seen_modules: set[str] = set()
    for manifest_path in manifests:
        manifest = _load_json(manifest_path)
        if manifest.get("schema") != "public_frontier_manifest_v1":
            raise SystemExit(f"{manifest_path}: unexpected manifest schema")
        _verify_manifest_hashes(manifest_path, manifest)
        seen_modules.add(
            _verify_manifest_contract(manifest_path, manifest, row_contracts)
        )

    toggle_receipts = sorted(
        FRONTIER_ROOT.glob("*/toggle_convention_receipt.json")
    ) + sorted(
        (POLICY_PATH.parent.parent / "athanor_artifacts").glob(
            "*/logs/*/toggle_convention_receipt.json"
        )
    )
    for receipt_path in toggle_receipts:
        _verify_toggle_receipt(receipt_path, policy)

    _verify_public_text()
    print(
        f"verified {len(manifests)} public manifests against {selected_toolchain_id}; "
        f"{len(toggle_receipts)} convention toggle receipt(s) checked"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
