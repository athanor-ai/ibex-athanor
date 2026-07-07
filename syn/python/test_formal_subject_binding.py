import hashlib
import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )


def _make_repo(tmp_path: Path, *, candidate_present: bool) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    target = repo / "rtl" / "target.sv"
    target.parent.mkdir()
    target.write_text("module target; wire keep = 1'b0; endmodule\n")
    _run(["git", "init"], repo)
    _run(["git", "add", "rtl/target.sv"], repo)
    _run(
        [
            "git",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-m",
            "baseline",
        ],
        repo,
    )

    patch = "\n".join(
        [
            "diff --git a/rtl/target.sv b/rtl/target.sv",
            "index 0000000..1111111 100644",
            "--- a/rtl/target.sv",
            "+++ b/rtl/target.sv",
            "@@ -1 +1 @@",
            "-module target; wire keep = 1'b0; endmodule",
            "+module target; wire keep = 1'b1; endmodule",
            "",
        ]
    )
    if candidate_present:
        target.write_text("module target; wire keep = 1'b1; endmodule\n")

    receipt_dir = repo / "athanor_artifacts" / "candidate" / "top_level_first"
    receipt_dir.mkdir(parents=True)
    patch_path = receipt_dir / "SOURCE_DIFF.patch"
    patch_path.write_text(patch)
    package_dir = receipt_dir.parent
    if candidate_present:
        (package_dir / "gate_source.sv").write_text(target.read_text())
    (receipt_dir / "top_level_first_receipt.json").write_text(
        json.dumps(
            {
                "schema": "athanor.top_level_first.v1",
                "artifact_hashes": {
                    "SOURCE_DIFF.patch": hashlib.sha256(patch.encode()).hexdigest()
                },
            }
        )
    )
    return repo


def test_formal_subject_binding_accepts_candidate_tree(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, candidate_present=True)

    result = _run(
        [
            "python3",
            str(REPO_ROOT / "athanor/check_formal_subject_binding.py"),
            "--repo-root",
            str(repo),
        ],
        REPO_ROOT,
    )

    assert "candidate patch is present in checkout" in result.stdout
    assert "rtl/target.sv" in result.stdout
    assert "1/1 receipts bound" in result.stdout


def test_formal_subject_binding_rejects_gate_source_mismatch(
    tmp_path: Path,
) -> None:
    repo = _make_repo(tmp_path, candidate_present=True)
    gate_source = repo / "athanor_artifacts" / "candidate" / "gate_source.sv"
    gate_source.write_text("module target; wire keep = 1'b0; endmodule\n")

    result = subprocess.run(
        [
            "python3",
            str(REPO_ROOT / "athanor/check_formal_subject_binding.py"),
            "--repo-root",
            str(repo),
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode != 0
    assert "does not match package gate_source.sv" in result.stderr


def test_formal_subject_binding_rejects_off_subject_baseline(
    tmp_path: Path,
) -> None:
    repo = _make_repo(tmp_path, candidate_present=False)

    result = subprocess.run(
        [
            "python3",
            str(REPO_ROOT / "athanor/check_formal_subject_binding.py"),
            "--repo-root",
            str(repo),
        ],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode != 0
    assert "SOURCE_DIFF.patch applies forward" in result.stderr
    assert "not the candidate subject" in result.stderr


def test_ci_formal_runs_subject_binding_before_nix() -> None:
    workflow = (REPO_ROOT / ".github/workflows/ci-formal.yml").read_text()

    subject_idx = workflow.index("python3 athanor/check_formal_subject_binding.py")
    nix_idx = workflow.index("uses: cachix/install-nix-action@v27")
    formal_idx = workflow.index("python3 conductor.py prove --check-complete")

    assert subject_idx < nix_idx < formal_idx
