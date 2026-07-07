"""ATH-2764: green-known / red-known fixtures for the proof-subject binding
assertion (athanor/verify_subject_binding.py).

The RED-KNOWN case is the exact shape that produced the #31 off-subject green
(head 12233fcf): the checkout carries the BASE RTL, the candidate rewrite lives
only in SOURCE_DIFF.patch, and the patch was never applied. The assertion MUST
red on that. These are also the green/red fixtures Bob's wiring-bite
meta-verifies the ci-formal steps against.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from athanor.verify_subject_binding import (
    _sha256,
    check_from_receipt,
    evaluate_subject_binding,
    main,
)

BASE = b"assign prefetch_branch = branch_req | nt_branch_mispredict_i;\n"
CANDIDATE = (
    b"if (BranchPredictor) begin : g_bp_prefetch_branch_mux\n  assign x = y;\nend\n"
)
# A minimal unified diff turning BASE into CANDIDATE (single hunk, whole-file).
PATCH = (
    b"--- a/rtl/ibex_if_stage.sv\n"
    b"+++ b/rtl/ibex_if_stage.sv\n"
    b"@@ -1 +1,3 @@\n"
    b"-assign prefetch_branch = branch_req | nt_branch_mispredict_i;\n"
    b"+if (BranchPredictor) begin : g_bp_prefetch_branch_mux\n"
    b"+  assign x = y;\n"
    b"+end\n"
)


# ---- pure verdict: green-known / red-known / tampered ---------------------


def test_green_known_bound_subject_passes():
    r = evaluate_subject_binding(
        checkout_bytes=CANDIDATE,
        reproduced_bytes=CANDIDATE,
        patch_bytes=PATCH,
        expected_patch_sha=_sha256(PATCH),
        base_commit="d36df4f",
        candidate="if_stage_no_bp_prefetch_direct",
    )
    assert r.match is True
    assert r.checkout_sha == r.reproduced_sha
    assert "subject bound" in r.reason


def test_red_known_off_subject_reds_the_12233fcf_shape():
    """Checkout is the BASE (patch never applied) -> proof would run off-subject.
    This is the incident shape; the assertion MUST red."""
    r = evaluate_subject_binding(
        checkout_bytes=BASE,  # <-- candidate NOT landed
        reproduced_bytes=CANDIDATE,
        patch_bytes=PATCH,
        expected_patch_sha=_sha256(PATCH),
        base_commit="d36df4f",
        candidate="if_stage_no_bp_prefetch_direct",
    )
    assert r.match is False
    assert "OFF-SUBJECT" in r.reason
    assert r.checkout_sha != r.reproduced_sha


def test_tampered_patch_reds():
    r = evaluate_subject_binding(
        checkout_bytes=CANDIDATE,
        reproduced_bytes=CANDIDATE,
        patch_bytes=PATCH,
        expected_patch_sha="00" * 32,  # receipt vouches a different patch
        base_commit="d36df4f",
        candidate="c",
    )
    assert r.match is False
    assert "patch tampered" in r.reason


# ---- I/O + real git-apply mechanic + fail-closed -------------------------


def _seed_repo(root: Path, tracked_if_stage: bytes) -> str:
    subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "t"], check=True)
    p = root / "rtl" / "ibex_if_stage.sv"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(BASE)  # the BASE commit carries base RTL
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "base"], check=True)
    sha = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    # Now make the WORKING TREE the candidate (as a real landed-RTL branch would)
    p.write_bytes(tracked_if_stage)
    return sha


def _write_receipt(root: Path, base_sha: str, patch_sha: str) -> Path:
    art = root / "art"
    art.mkdir()
    (art / "SOURCE_DIFF.patch").write_bytes(PATCH)
    receipt = art / "top_level_first_receipt.json"
    receipt.write_text(
        json.dumps(
            {
                "base_commit": base_sha,
                "candidate": "if_stage_no_bp_prefetch_direct",
                "artifact_hashes": {"SOURCE_DIFF.patch": patch_sha},
            }
        )
    )
    return receipt


def test_integration_landed_candidate_binds(tmp_path):
    base_sha = _seed_repo(tmp_path, tracked_if_stage=CANDIDATE)  # candidate landed
    receipt = _write_receipt(tmp_path, base_sha, _sha256(PATCH))
    r = check_from_receipt(
        receipt_path=receipt,
        repo=tmp_path,
        candidate_rel_path="rtl/ibex_if_stage.sv",
        patch_path=tmp_path / "art" / "SOURCE_DIFF.patch",
    )
    assert r.match is True, r.reason


def test_integration_off_subject_reds(tmp_path):
    # candidate NOT landed: working tree still BASE (the 12233fcf case)
    base_sha = _seed_repo(tmp_path, tracked_if_stage=BASE)
    receipt = _write_receipt(tmp_path, base_sha, _sha256(PATCH))
    r = check_from_receipt(
        receipt_path=receipt,
        repo=tmp_path,
        candidate_rel_path="rtl/ibex_if_stage.sv",
        patch_path=tmp_path / "art" / "SOURCE_DIFF.patch",
    )
    assert r.match is False
    assert "OFF-SUBJECT" in r.reason


def test_cli_exit_codes(tmp_path):
    base_sha = _seed_repo(tmp_path, tracked_if_stage=CANDIDATE)
    receipt = _write_receipt(tmp_path, base_sha, _sha256(PATCH))
    emit = tmp_path / "subject_binding.json"
    rc = main(
        [
            "--receipt",
            str(receipt),
            "--repo",
            str(tmp_path),
            "--patch",
            str(tmp_path / "art" / "SOURCE_DIFF.patch"),
            "--emit",
            str(emit),
        ]
    )
    assert rc == 0
    emitted = json.loads(emit.read_text())
    assert emitted["match"] is True
    assert emitted["checkout_sha"] == emitted["reproduced_sha"]


def test_fail_closed_missing_base_commit(tmp_path):
    _seed_repo(tmp_path, tracked_if_stage=CANDIDATE)
    art = tmp_path / "art"
    art.mkdir()
    (art / "SOURCE_DIFF.patch").write_bytes(PATCH)
    bad = art / "r.json"
    bad.write_text(
        json.dumps({"artifact_hashes": {"SOURCE_DIFF.patch": _sha256(PATCH)}})
    )
    rc = main(
        [
            "--receipt",
            str(bad),
            "--repo",
            str(tmp_path),
            "--patch",
            str(art / "SOURCE_DIFF.patch"),
        ]
    )
    assert rc == 3  # fail-closed, not a silent pass
