#!/usr/bin/env python3
"""Verify public Ibex receipt manifests and selected-toolchain policy."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
POLICY_PATH = ROOT / "toolchain_policy.json"
FRONTIER_ROOT = ROOT / "ppa_frontier"
PUBLIC_TEXT_PATHS = [ROOT.parent / "README.md", ROOT / "README.md", FRONTIER_ROOT / "README.md"]


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
            raise SystemExit(f"{manifest_path}: artifact {artifact_name} must be an object")
        rel_path = artifact_ref.get("path")
        expected_sha = artifact_ref.get("sha256")
        if not isinstance(rel_path, str) or not isinstance(expected_sha, str):
            raise SystemExit(f"{manifest_path}: artifact {artifact_name} missing path or sha256")
        artifact_path = module_dir / rel_path
        if not artifact_path.is_file():
            raise SystemExit(f"{manifest_path}: artifact {rel_path} does not exist")
        actual_sha = _sha256(artifact_path)
        if actual_sha != expected_sha:
            raise SystemExit(
                f"{manifest_path}: artifact {rel_path} sha256 mismatch "
                f"(expected {expected_sha}, got {actual_sha})"
            )


def _verify_alu_row(manifest_path: Path, manifest: dict[str, Any], selected_toolchain_id: str) -> None:
    policy = manifest.get("toolchain_policy")
    if not isinstance(policy, dict):
        raise SystemExit(f"{manifest_path}: missing toolchain_policy")
    if policy.get("selected_toolchain_id") != selected_toolchain_id:
        raise SystemExit(f"{manifest_path}: ALU row must use selected Yosys 0.66 toolchain")
    if policy.get("customer_status") != "customer_area_tradeoff_yosys66":
        raise SystemExit(f"{manifest_path}: ALU row must be classified as area tradeoff, not full PPA")
    if policy.get("full_ppa_frontier") is not False:
        raise SystemExit(f"{manifest_path}: timing-hostile ALU row must not be full_ppa_frontier")
    area_receipt = policy.get("selected_area_receipt")
    timing_receipt = policy.get("selected_timing_receipt")
    if area_receipt != "area_yosys66.json" or timing_receipt != "toggle_timing_yosys66.json":
        raise SystemExit(f"{manifest_path}: ALU row must point to Yosys 0.66 area/timing receipts")

    area = _load_json(manifest_path.parent / "area_yosys66.json")
    timing = _load_json(manifest_path.parent / "toggle_timing_yosys66.json")
    if area.get("toolchain", {}).get("yosys") != "Yosys 0.66+181":
        raise SystemExit(f"{manifest_path}: area_yosys66.json is not Yosys 0.66+181")
    propagation = timing.get("propagation_delay")
    if not isinstance(propagation, dict):
        raise SystemExit(f"{manifest_path}: missing propagation_delay timing block")
    if propagation.get("status") != "regression":
        raise SystemExit(f"{manifest_path}: ALU timing tradeoff must record propagation-delay regression")
    if propagation.get("timing_convention") != "combinational_max_propagation_delay":
        raise SystemExit(f"{manifest_path}: ALU row must record max-propagation-delay timing convention")
    if float(propagation.get("gate_delay_ns", 0.0)) <= float(propagation.get("gold_delay_ns", 0.0)):
        raise SystemExit(f"{manifest_path}: ALU timing tradeoff requires gate delay > gold delay")


def _verify_cross_tool_sensitive_row(manifest_path: Path, manifest: dict[str, Any]) -> None:
    policy = manifest.get("toolchain_policy")
    if not isinstance(policy, dict):
        raise SystemExit(f"{manifest_path}: missing toolchain_policy")
    if policy.get("customer_status") != "formal_only_cross_tool_sensitive_rebaseline_pending":
        raise SystemExit(f"{manifest_path}: compressed decoder must remain rebaseline-pending")
    if policy.get("customer_frontier") is not False:
        raise SystemExit(f"{manifest_path}: cross-tool-sensitive row must not be customer frontier")
    if policy.get("full_ppa_frontier") is not False:
        raise SystemExit(f"{manifest_path}: cross-tool-sensitive row must not be full PPA frontier")
    sensitivity = _load_json(manifest_path.parent / "area.json").get("toolchain_sensitivity")
    if not isinstance(sensitivity, dict) or sensitivity.get("classification") != "cross_tool_sensitive":
        raise SystemExit(f"{manifest_path}: missing cross-tool sensitivity evidence")


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
            raise SystemExit(f"{receipt_path}: toggle receipt missing hash-pinned {field}")
    if receipt.get("no_x_or_z_on_primary_inputs") != "construction_guaranteed_binary_assignments":
        raise SystemExit(
            f"{receipt_path}: toggle receipt missing no_x_or_z_on_primary_inputs "
            "construction guarantee"
        )
    for name_field, hash_field in (("trace", "trace_sha256"), ("vcd", "vcd_sha256")):
        rel = receipt.get(name_field)
        if rel:
            candidate = receipt_path.parent / rel
            if candidate.is_file() and _sha256(candidate) != receipt[hash_field]:
                raise SystemExit(f"{receipt_path}: {name_field} file does not match {hash_field}")
            if name_field == "vcd" and _sha256_vcd_normalized(candidate) != receipt[
                "normalized_vcd_sha256"
            ]:
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
    conv_sha = hashlib.sha256(json.dumps(conv, indent=4, sort_keys=True).encode()).hexdigest()
    good = {
        "convention_id": conv["id"],
        "convention_sha256": conv_sha,
        "trace_sha256": "0" * 64,
        "vcd_sha256": "1" * 64,
        "normalized_vcd_sha256": "4" * 64,
        "gold_sha256": "2" * 64,
        "gate_sha256": "3" * 64,
        "no_x_or_z_on_primary_inputs": "construction_guaranteed_binary_assignments",
    }
    cases = [
        ("conforming", good, True),
        ("unlabeled", {k: v for k, v in good.items() if k != "convention_id"}, False),
        ("wrong_convention", {**good, "convention_id": "scratch_trace_v0"}, False),
        ("edited_convention", {**good, "convention_sha256": "f" * 64}, False),
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
        for name, receipt, should_pass in cases:
            rp = Path(td) / f"{name}.json"
            rp.write_text(json.dumps(receipt))
            try:
                _verify_toggle_receipt(rp, policy)
                outcome = True
            except SystemExit:
                outcome = False
            if outcome != should_pass:
                raise SystemExit(f"selftest case {name!r}: expected pass={should_pass}, got {outcome}")
    print(f"toggle-gate selftest: {len(cases)}/{len(cases)} cases behave as required")


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
                raise SystemExit(f"{path}: public text contains internal token {token!r}")


def main() -> int:
    if "--selftest" in sys.argv:
        _selftest_toggle_gate()
        return 0
    policy = _load_json(POLICY_PATH)
    selected = policy.get("selected_toolchain")
    if not isinstance(selected, dict):
        raise SystemExit(f"{POLICY_PATH}: missing selected_toolchain")
    selected_toolchain_id = selected.get("id")
    if selected_toolchain_id != "yosys_0_66_181_oss_cad_suite_2026_06_30":
        raise SystemExit(f"{POLICY_PATH}: selected toolchain must be Yosys 0.66+181")

    manifests = sorted(FRONTIER_ROOT.glob("*/manifest.json"))
    if not manifests:
        raise SystemExit(f"{FRONTIER_ROOT}: no module manifests found")

    for manifest_path in manifests:
        manifest = _load_json(manifest_path)
        if manifest.get("schema") != "public_frontier_manifest_v1":
            raise SystemExit(f"{manifest_path}: unexpected manifest schema")
        _verify_manifest_hashes(manifest_path, manifest)
        module = manifest.get("module")
        if module == "ibex_alu":
            _verify_alu_row(manifest_path, manifest, selected_toolchain_id)
        elif module == "ibex_compressed_decoder":
            _verify_cross_tool_sensitive_row(manifest_path, manifest)
        else:
            raise SystemExit(f"{manifest_path}: unrecognized public module {module!r}")

    toggle_receipts = sorted(FRONTIER_ROOT.glob("*/toggle_convention_receipt.json")) + sorted(
        (POLICY_PATH.parent.parent / "athanor_artifacts").glob("*/logs/*/toggle_convention_receipt.json")
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
