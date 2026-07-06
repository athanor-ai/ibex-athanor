#!/usr/bin/env python3
"""ATH-2764 (Lane-3 formal half): proof-SUBJECT binding assertion.

A green OSS-FV proves whatever RTL the checkout contained. On #31 head
12233fcf the run was sound AND obligation-complete (298/298 UNSAT,
`conductor.py prove --check-complete`) yet proved the WRONG SUBJECT: the
candidate no-BP prefetch rewrite lived only in SOURCE_DIFF.patch and the
workflow never applied it, so the receipt proved the *repository* RTL, not
the candidate. `--check-complete` answers "did we discharge every obligation
we set up?" -- NOT "is the thing we set up the candidate?".

This guard closes that gap, in the acceptance decision path (not a reviewer's
eyeball): it asserts the checked-out candidate file is EXACTLY the candidate
reproduced by applying the receipt's SOURCE_DIFF.patch to the receipt's pinned
base_commit -- byte-for-byte -- and emits the bound hashes into a
subject_binding receipt so downstream sees WHAT was proven, not just THAT it
passed. Fail-closed: any mismatch / missing input exits nonzero BEFORE a green
prove can be claimed.

The proven-tree <-> candidate binding is anchored to the PATCH APPLIED TO THE
PINNED BASE, not to a receipt-recorded RTL hash, so the same drift that
produced the off-subject green (checkout != candidate) cannot also satisfy the
check.

Homes/wiring (ci-formal.yml steps, the candidate-present precondition, and the
subprocess wiring-bite) are Bob's slices under ATH-2764 / ATH-2699. This module
is the formal-side assertion + its own green-known/red-known unit test.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class BindingResult:
    match: bool
    reason: str
    base_commit: str
    candidate: str
    patch_sha: str
    expected_patch_sha: str
    reproduced_sha: str
    checkout_sha: str

    def as_receipt(self) -> dict:
        return asdict(self)


def evaluate_subject_binding(
    *,
    checkout_bytes: bytes,
    reproduced_bytes: bytes,
    patch_bytes: bytes,
    expected_patch_sha: str,
    base_commit: str,
    candidate: str,
) -> BindingResult:
    """PURE verdict: no git, no fs. Given the checked-out candidate file, the
    candidate reproduced by applying the patch to the pinned base, and the
    patch itself, decide whether the proven subject IS the candidate.

    Two independent bindings must BOTH hold:
      1. patch integrity: sha256(patch) == the receipt's recorded patch hash
         (the patch we reproduce from is the one the receipt vouches for).
      2. subject identity: sha256(checkout) == sha256(reproduced)
         (the tree under proof is the patch-applied-to-base candidate).
    """
    patch_sha = _sha256(patch_bytes)
    reproduced_sha = _sha256(reproduced_bytes)
    checkout_sha = _sha256(checkout_bytes)

    def result(match: bool, reason: str) -> BindingResult:
        return BindingResult(
            match=match,
            reason=reason,
            base_commit=base_commit,
            candidate=candidate,
            patch_sha=patch_sha,
            expected_patch_sha=expected_patch_sha,
            reproduced_sha=reproduced_sha,
            checkout_sha=checkout_sha,
        )

    if patch_sha != expected_patch_sha:
        return result(
            False,
            f"patch tampered: sha256(SOURCE_DIFF.patch)={patch_sha} != "
            f"receipt-recorded {expected_patch_sha}",
        )
    if checkout_sha != reproduced_sha:
        return result(
            False,
            f"OFF-SUBJECT: checkout candidate sha256={checkout_sha} != "
            f"patch-applied-to-{base_commit[:9]} sha256={reproduced_sha} "
            "(the proof would run on RTL that is not the candidate)",
        )
    return result(
        True,
        f"subject bound: checkout == SOURCE_DIFF.patch applied to "
        f"{base_commit[:9]} (sha256 {checkout_sha}); patch integrity ok",
    )


def _reproduce_candidate(
    repo: Path, base_commit: str, rel_path: str, patch_bytes: bytes
) -> bytes:
    """Apply patch_bytes to (base_commit:rel_path) and return the result bytes.

    Uses git to materialise the pinned base blob and `git apply` for a strict,
    context-checked application (rejects fuzz). Raises on unreachable base or a
    patch that does not apply cleanly -- both are fail-closed conditions.
    """
    base_blob = subprocess.run(
        ["git", "-C", str(repo), "show", f"{base_commit}:{rel_path}"],
        capture_output=True,
        check=True,
    ).stdout
    # `git apply` reads the target from the working tree; drive it via a temp
    # tree seeded with the pinned base blob so application is against base, not
    # the checkout.
    import tempfile

    with tempfile.TemporaryDirectory(prefix="subject_binding_") as td:
        work = Path(td)
        target = work / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(base_blob)
        patch_file = work / "candidate.patch"
        patch_file.write_bytes(patch_bytes)
        subprocess.run(
            [
                "git",
                "-C",
                str(work),
                "apply",
                "--unsafe-paths",
                "--directory",
                str(work),
                str(patch_file),
            ],
            check=True,
            capture_output=True,
        )
        return target.read_bytes()


def check_from_receipt(
    *,
    receipt_path: Path,
    repo: Path,
    candidate_rel_path: str,
    patch_path: Path,
) -> BindingResult:
    """Fail-closed I/O wrapper: load the receipt, reproduce the candidate from
    the pinned base + patch, and evaluate the pure binding verdict."""
    receipt = json.loads(receipt_path.read_text())
    base_commit = receipt["base_commit"]  # KeyError = fail-closed missing field
    expected_patch_sha = receipt["artifact_hashes"]["SOURCE_DIFF.patch"]
    candidate = receipt.get("candidate", "<unnamed>")

    patch_bytes = patch_path.read_bytes()
    checkout_bytes = (repo / candidate_rel_path).read_bytes()
    reproduced_bytes = _reproduce_candidate(
        repo, base_commit, candidate_rel_path, patch_bytes
    )

    return evaluate_subject_binding(
        checkout_bytes=checkout_bytes,
        reproduced_bytes=reproduced_bytes,
        patch_bytes=patch_bytes,
        expected_patch_sha=expected_patch_sha,
        base_commit=base_commit,
        candidate=candidate,
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="ATH-2764 proof-subject binding assertion")
    ap.add_argument(
        "--receipt", required=True, type=Path, help="top_level_first_receipt.json"
    )
    ap.add_argument(
        "--repo", default=Path("."), type=Path, help="repo root (default: cwd)"
    )
    ap.add_argument(
        "--candidate-file",
        default="rtl/ibex_if_stage.sv",
        help="repo-relative path of the candidate RTL under proof",
    )
    ap.add_argument(
        "--patch",
        type=Path,
        default=None,
        help="SOURCE_DIFF.patch (default: alongside the receipt)",
    )
    ap.add_argument(
        "--emit", type=Path, default=None, help="write subject_binding.json here"
    )
    args = ap.parse_args(argv)

    patch_path = args.patch or (args.receipt.parent / "SOURCE_DIFF.patch")

    try:
        result = check_from_receipt(
            receipt_path=args.receipt,
            repo=args.repo,
            candidate_rel_path=args.candidate_file,
            patch_path=patch_path,
        )
    except (KeyError, FileNotFoundError, subprocess.CalledProcessError) as exc:
        # Fail-closed: any missing input / unreachable base / non-applying patch
        # is a binding failure, never a silent pass.
        print(
            f"SUBJECT-BINDING FAIL-CLOSED: {type(exc).__name__}: {exc}", file=sys.stderr
        )
        return 3

    if args.emit:
        args.emit.write_text(json.dumps(result.as_receipt(), indent=2))

    if result.match:
        print(f"SUBJECT-BINDING OK: {result.reason}")
        return 0
    print(f"SUBJECT-BINDING RED: {result.reason}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
