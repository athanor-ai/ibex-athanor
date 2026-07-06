#!/usr/bin/env python3
"""Check that hosted OSS-FV proves the candidate tree, not stale baseline RTL.

ATH-2764: a prior green OSS-FV run proved the repository checkout while the
candidate RTL lived only in an artifact SOURCE_DIFF.patch. This gate binds each
top-level candidate receipt to the checked-out tree before the expensive formal
flow starts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"{path}: expected JSON object")
    return data


def _git_apply_check(
    repo_root: Path, patch: Path, *, reverse: bool
) -> subprocess.CompletedProcess[str]:
    cmd = ["git", "apply", "--check", "--whitespace=nowarn"]
    if reverse:
        cmd.append("--reverse")
    cmd.append(str(patch.relative_to(repo_root)))
    return subprocess.run(
        cmd,
        cwd=repo_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def _patch_targets(patch: Path) -> list[Path]:
    targets: list[Path] = []
    for line in patch.read_text(encoding="utf-8").splitlines():
        if not line.startswith("+++ b/"):
            continue
        rel = line.removeprefix("+++ b/")
        if rel == "/dev/null":
            continue
        path = Path(rel)
        if path not in targets:
            targets.append(path)
    if not targets:
        raise SystemExit(f"{patch}: no target files found in SOURCE_DIFF.patch")
    return targets


def _bind_targets_to_sources(
    repo_root: Path, receipt_path: Path, receipt: dict[str, Any], targets: list[Path]
) -> None:
    """Bind each proven target back to a package source artifact (ATH-2764 fast-follow).

    Authority (Ronald 2026-07-06): when the receipt carries a ``gate_sources`` map it is
    authoritative and must bind every patch target exactly once, chaining
    ``checkout target sha == artifact file sha == artifact_hashes[artifact-path]``.
    Single-target legacy receipts may keep package-root ``gate_source.sv`` for now, but a
    multi-target patch with no ``gate_sources`` is UNBINDABLE and fails closed — the prior
    gate silently skipped multi-target binding, a subject-binding vacuity.
    """
    package_dir = receipt_path.parent.parent
    artifact_hashes = receipt.get("artifact_hashes", {})
    gate_sources = receipt.get("gate_sources")

    if gate_sources is None:
        if len(targets) == 1:
            gate_source = package_dir / "gate_source.sv"
            if gate_source.is_file():  # back-compat single-target binding
                target_sha = _sha256(repo_root / targets[0])
                gate_sha = _sha256(gate_source)
                if target_sha != gate_sha:
                    raise SystemExit(
                        f"{receipt_path}: checked-out {targets[0]} sha256 {target_sha} "
                        f"does not match package gate_source.sv sha256 {gate_sha}"
                    )
            return
        raise SystemExit(
            f"{receipt_path}: multi-target SOURCE_DIFF.patch ({len(targets)} targets) has "
            "no gate_sources binding map; unbindable (fail-closed). Add a "
            'gate_sources: {"<target-path>": "<artifact-path>"} field binding every target.'
        )

    if not isinstance(gate_sources, dict):
        raise SystemExit(f"{receipt_path}: gate_sources must be an object "
                         '{"<target-path>": "<artifact-path>"}')
    target_keys = {str(t) for t in targets}
    gs_keys = set(gate_sources)
    missing = target_keys - gs_keys
    if missing:
        raise SystemExit(
            f"{receipt_path}: gate_sources does not bind patch target(s) {sorted(missing)}")
    extra = gs_keys - target_keys
    if extra:
        raise SystemExit(
            f"{receipt_path}: gate_sources has key(s) not in the patch: {sorted(extra)}")

    package_res = package_dir.resolve()
    for target in sorted(target_keys):
        artifact_rel = gate_sources[target]
        artifact_path = (package_dir / artifact_rel).resolve()
        if package_res != artifact_path and package_res not in artifact_path.parents:
            raise SystemExit(
                f"{receipt_path}: gate_sources[{target!r}] artifact {artifact_rel!r} "
                "points outside the package")
        if not artifact_path.is_file():
            raise SystemExit(
                f"{receipt_path}: gate_sources[{target!r}] artifact {artifact_rel!r} "
                "is missing from the package")
        declared = artifact_hashes.get(artifact_rel)
        if declared is None:
            raise SystemExit(
                f"{receipt_path}: artifact_hashes has no entry for gate_sources artifact "
                f"{artifact_rel!r}")
        artifact_sha = _sha256(artifact_path)
        if artifact_sha != declared:
            raise SystemExit(
                f"{receipt_path}: artifact {artifact_rel!r} sha256 {artifact_sha} does not "
                f"match artifact_hashes entry {declared}")
        checkout_sha = _sha256(repo_root / target)
        if checkout_sha != artifact_sha:
            raise SystemExit(
                f"{receipt_path}: checked-out {target} sha256 {checkout_sha} does not match "
                f"bound source artifact {artifact_rel!r} sha256 {artifact_sha}")


def _check_receipt(repo_root: Path, receipt_path: Path) -> str:
    receipt = _load_json(receipt_path)
    if receipt.get("schema") != "athanor.top_level_first.v1":
        raise SystemExit(f"{receipt_path}: expected athanor.top_level_first.v1 schema")

    patch_path = receipt_path.parent / "SOURCE_DIFF.patch"
    if not patch_path.is_file():
        raise SystemExit(f"{receipt_path}: missing SOURCE_DIFF.patch")

    expected_patch_sha = receipt.get("artifact_hashes", {}).get("SOURCE_DIFF.patch")
    if expected_patch_sha is None:
        raise SystemExit(
            f"{receipt_path}: artifact_hashes.SOURCE_DIFF.patch is required in an "
            "athanor.top_level_first.v1 receipt (fail-closed: the patch-blob integrity "
            "leg must not silently skip when the hash is absent)"
        )
    actual_patch_sha = _sha256(patch_path)
    if actual_patch_sha != expected_patch_sha:
        raise SystemExit(
            f"{receipt_path}: SOURCE_DIFF.patch sha256 mismatch "
            f"(expected {expected_patch_sha}, got {actual_patch_sha})"
        )

    reverse = _git_apply_check(repo_root, patch_path, reverse=True)
    if reverse.returncode == 0:
        target_hashes = []
        targets = _patch_targets(patch_path)
        for target in targets:
            target_path = repo_root / target
            if not target_path.is_file():
                raise SystemExit(
                    f"{receipt_path}: patch target {target} is absent from checkout"
                )
            target_hashes.append(f"{target}:{_sha256(target_path)}")

        _bind_targets_to_sources(repo_root, receipt_path, receipt, targets)

        rel = receipt_path.relative_to(repo_root)
        return f"{rel}: candidate patch is present in checkout ({', '.join(target_hashes)})"

    forward = _git_apply_check(repo_root, patch_path, reverse=False)
    if forward.returncode == 0:
        raise SystemExit(
            f"{receipt_path}: SOURCE_DIFF.patch applies forward to this checkout. "
            "Hosted OSS-FV would prove the baseline tree, not the candidate subject."
        )

    raise SystemExit(
        f"{receipt_path}: checkout does not match the candidate patch and is not "
        "the patch baseline either. Reverse-check stderr:\n"
        f"{reverse.stderr.strip()}\nForward-check stderr:\n{forward.stderr.strip()}"
    )


def _iter_top_level_receipts(repo_root: Path) -> list[Path]:
    artifacts = repo_root / "athanor_artifacts"
    if not artifacts.is_dir():
        return []
    return sorted(artifacts.glob("*/top_level_first/top_level_first_receipt.json"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="repository checkout to validate (default: this repo)",
    )
    args = parser.parse_args(argv)
    repo_root = args.repo_root.resolve()

    receipts = _iter_top_level_receipts(repo_root)
    if not receipts:
        print("formal subject binding: no top-level candidate receipts found")
        return 0

    for receipt_path in receipts:
        print(_check_receipt(repo_root, receipt_path.resolve()))
    print(f"formal subject binding: {len(receipts)}/{len(receipts)} receipts bound")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
