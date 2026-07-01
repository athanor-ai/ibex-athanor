#!/usr/bin/env python3
"""Verify public Ibex frontier manifests against the pinned toolchain policy."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
POLICY_PATH = ROOT / "toolchain_policy.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise AssertionError(f"{path}: expected top-level JSON object")
    return data


def _contains_mapping_value(value: Any, key: str, expected: Any) -> bool:
    if isinstance(value, dict):
        if value.get(key) == expected:
            return True
        return any(_contains_mapping_value(child, key, expected) for child in value.values())
    if isinstance(value, list):
        return any(_contains_mapping_value(child, key, expected) for child in value)
    return False


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _verify_artifact_hashes(manifest_path: Path, manifest: dict[str, Any]) -> None:
    artifacts = manifest.get("artifacts")
    _require(isinstance(artifacts, dict) and artifacts, f"{manifest_path}: missing artifacts")

    manifest_dir = manifest_path.parent
    for label, entry in artifacts.items():
        _require(isinstance(entry, dict), f"{manifest_path}: artifact {label} must be an object")
        rel_path = entry.get("path")
        expected_sha = entry.get("sha256")
        _require(isinstance(rel_path, str) and rel_path, f"{manifest_path}: artifact {label} missing path")
        _require(
            isinstance(expected_sha, str) and len(expected_sha) == 64,
            f"{manifest_path}: artifact {label} missing sha256",
        )
        artifact_path = manifest_dir / rel_path
        _require(artifact_path.is_file(), f"{manifest_path}: artifact {rel_path} missing")
        actual_sha = _sha256(artifact_path)
        _require(
            actual_sha == expected_sha,
            f"{manifest_path}: artifact {rel_path} sha256 mismatch: {actual_sha} != {expected_sha}",
        )


def _verify_policy_ref(
    manifest_path: Path,
    manifest: dict[str, Any],
    policy: dict[str, Any],
    policy_sha: str,
) -> dict[str, Any]:
    toolchain_policy = manifest.get("toolchain_policy")
    _require(isinstance(toolchain_policy, dict), f"{manifest_path}: missing toolchain_policy")

    requirements = policy["manifest_requirements"]
    expected_policy_ref = requirements["policy_ref"]
    _require(
        toolchain_policy.get("policy_ref") == expected_policy_ref,
        f"{manifest_path}: policy_ref must be {expected_policy_ref}",
    )
    _require(
        toolchain_policy.get("policy_sha256") == policy_sha,
        f"{manifest_path}: policy_sha256 must match {POLICY_PATH.name}",
    )
    _require(
        toolchain_policy.get("policy_id") == policy["policy_id"],
        f"{manifest_path}: policy_id mismatch",
    )
    _require(
        toolchain_policy.get("selected_toolchain_id")
        == policy["selected_toolchain"]["toolchain_id"],
        f"{manifest_path}: selected_toolchain_id mismatch",
    )
    return toolchain_policy


def _verify_current_customer_row(
    manifest_path: Path,
    manifest: dict[str, Any],
    toolchain_policy: dict[str, Any],
    policy: dict[str, Any],
) -> None:
    if toolchain_policy.get("customer_facing_status") != "current_customer_rebaseline":
        _require(
            toolchain_policy.get("customer_facing_status")
            in {
                "historical_cross_tool_sensitive_rebaseline_pending",
                "archived_not_customer_facing",
                "current_customer_rebaseline",
            },
            f"{manifest_path}: unknown customer_facing_status",
        )
        _require(
            toolchain_policy.get("selected_toolchain_required") is False,
            f"{manifest_path}: non-current rows must not claim selected_toolchain_required",
        )
        _require(
            toolchain_policy.get("full_ppa_frontier") is False,
            f"{manifest_path}: non-current rows must not claim full_ppa_frontier",
        )
        return

    _require(
        toolchain_policy.get("selected_toolchain_required") is True,
        f"{manifest_path}: current customer rows require selected toolchain",
    )
    expected_timing = policy["timing"]["customer_facing_convention"]
    _require(
        toolchain_policy.get("timing_convention") == expected_timing,
        f"{manifest_path}: timing_convention must be {expected_timing}",
    )

    receipt_names = toolchain_policy.get("selected_toolchain_receipts")
    _require(
        isinstance(receipt_names, list) and receipt_names,
        f"{manifest_path}: current customer row missing selected_toolchain_receipts",
    )
    artifact_names = set(manifest["artifacts"])
    selected_toolchain = policy["selected_toolchain"]
    for receipt_name in receipt_names:
        _require(isinstance(receipt_name, str), f"{manifest_path}: receipt names must be strings")
        _require(receipt_name in artifact_names, f"{manifest_path}: receipt {receipt_name} absent from artifacts")
        receipt = _load_json(manifest_path.parent / receipt_name)
        _require(
            _contains_mapping_value(receipt, "yosys", selected_toolchain["yosys"]),
            f"{manifest_path}: {receipt_name} does not record {selected_toolchain['yosys']}",
        )
        _require(
            _contains_mapping_value(receipt, "oss_cad_suite_release", selected_toolchain["oss_cad_suite_release"]),
            f"{manifest_path}: {receipt_name} does not record OSS CAD Suite release",
        )

    if toolchain_policy.get("timing_convention") == "combinational_max_propagation_delay":
        timing_receipt_name = toolchain_policy.get("timing_receipt")
        _require(isinstance(timing_receipt_name, str), f"{manifest_path}: missing timing_receipt")
        timing_receipt = _load_json(manifest_path.parent / timing_receipt_name)
        propagation_delay = timing_receipt.get("propagation_delay")
        _require(
            isinstance(propagation_delay, dict),
            f"{manifest_path}: {timing_receipt_name} missing propagation_delay",
        )
        _require(
            propagation_delay.get("timing_convention") == "combinational_max_propagation_delay",
            f"{manifest_path}: {timing_receipt_name} missing max-delay timing convention",
        )
        _require(
            isinstance(propagation_delay.get("gold_delay_ns"), (int, float))
            and isinstance(propagation_delay.get("gate_delay_ns"), (int, float)),
            f"{manifest_path}: {timing_receipt_name} missing gold/gate max-delay values",
        )


def verify(root: Path) -> list[Path]:
    policy_path = root / "toolchain_policy.json"
    policy = _load_json(policy_path)
    _require(policy.get("schema") == "athanor_ibex_toolchain_policy_v1", "invalid policy schema")
    _require(policy["selected_toolchain"]["yosys"] == "Yosys 0.66+181", "unexpected selected Yosys")
    _require(
        policy["timing"]["unconstrained_opensta_is_customer_evidence"] is False,
        "unconstrained OpenSTA must not be customer evidence",
    )
    policy_sha = _sha256(policy_path)

    manifests = sorted(path for path in root.glob("*/manifest.json") if path.is_file())
    _require(manifests, "no module manifests found")
    for manifest_path in manifests:
        manifest = _load_json(manifest_path)
        _require(
            manifest.get("schema") == policy["manifest_requirements"]["required_manifest_schema"],
            f"{manifest_path}: unexpected manifest schema",
        )
        _verify_artifact_hashes(manifest_path, manifest)
        toolchain_policy = _verify_policy_ref(manifest_path, manifest, policy, policy_sha)
        _verify_current_customer_row(manifest_path, manifest, toolchain_policy, policy)
    return manifests


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="PPA frontier root containing toolchain_policy.json and module manifests.",
    )
    args = parser.parse_args()
    manifests = verify(args.root.resolve())
    print(f"verified {len(manifests)} manifest(s) against pinned toolchain policy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
