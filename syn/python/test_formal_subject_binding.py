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


# --------------------------------------------------------------- ATH-2764 fast-follow
# Close two silent-skip subject-binding vacuities (Quan's #35 review notes, Ronald ratify
# design (A) gate_sources): a receipt missing artifact_hashes.SOURCE_DIFF.patch must not
# skip the hash leg, and a multi-target patch must bind EACH target to a package source
# artifact (or red as unbindable) rather than silently pass.

def _gate(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(REPO_ROOT / "athanor/check_formal_subject_binding.py"),
         "--repo-root", str(repo)],
        cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=False,
    )


def _make_multi_target_repo(tmp_path: Path, *, with_gate_sources: bool,
                            mismatch_target: str | None = None) -> Path:
    """Two-target candidate package. gate_sources binds each target to a per-target source
    artifact; ``mismatch_target`` writes a divergent bound artifact for that one target."""
    repo = tmp_path / "repo"
    (repo / "rtl").mkdir(parents=True)
    names = ["a", "b"]
    baseline = {n: f"module {n}; wire keep = 1'b0; endmodule\n" for n in names}
    candidate = {n: f"module {n}; wire keep = 1'b1; endmodule\n" for n in names}
    for n in names:
        (repo / "rtl" / f"{n}.sv").write_text(baseline[n])
    _run(["git", "init"], repo)
    _run(["git", "add", "-A"], repo)
    _run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.com",
          "commit", "-m", "baseline"], repo)

    patch_blocks = []
    for n in names:
        patch_blocks += [
            f"diff --git a/rtl/{n}.sv b/rtl/{n}.sv",
            "index 0000000..1111111 100644",
            f"--- a/rtl/{n}.sv",
            f"+++ b/rtl/{n}.sv",
            "@@ -1 +1 @@",
            f"-{baseline[n].rstrip()}",
            f"+{candidate[n].rstrip()}",
        ]
    patch = "\n".join(patch_blocks) + "\n"
    for n in names:  # candidate present in the checkout
        (repo / "rtl" / f"{n}.sv").write_text(candidate[n])

    receipt_dir = repo / "athanor_artifacts" / "candidate" / "top_level_first"
    receipt_dir.mkdir(parents=True)
    (receipt_dir / "SOURCE_DIFF.patch").write_text(patch)
    package_dir = receipt_dir.parent

    artifact_hashes = {"SOURCE_DIFF.patch": hashlib.sha256(patch.encode()).hexdigest()}
    receipt: dict = {"schema": "athanor.top_level_first.v1"}
    if with_gate_sources:
        (package_dir / "sources").mkdir()
        gate_sources = {}
        for n in names:
            content = candidate[n]
            if mismatch_target == f"rtl/{n}.sv":
                content = "module x; wire keep = 1'bx; endmodule\n"  # diverges from checkout
            art_rel = f"sources/{n}.sv"
            (package_dir / art_rel).write_text(content)
            artifact_hashes[art_rel] = hashlib.sha256(content.encode()).hexdigest()
            gate_sources[f"rtl/{n}.sv"] = art_rel
        receipt["gate_sources"] = gate_sources
    receipt["artifact_hashes"] = artifact_hashes
    (receipt_dir / "top_level_first_receipt.json").write_text(json.dumps(receipt))
    return repo


def test_missing_source_diff_hash_is_rejected(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, candidate_present=True)
    receipt_path = (repo / "athanor_artifacts" / "candidate" / "top_level_first"
                    / "top_level_first_receipt.json")
    receipt = json.loads(receipt_path.read_text())
    del receipt["artifact_hashes"]["SOURCE_DIFF.patch"]  # strip the hash -> must not skip
    receipt_path.write_text(json.dumps(receipt))

    result = _gate(repo)
    assert result.returncode != 0
    assert "artifact_hashes.SOURCE_DIFF.patch is required" in result.stderr


def test_multi_target_without_gate_sources_is_unbindable(tmp_path: Path) -> None:
    repo = _make_multi_target_repo(tmp_path, with_gate_sources=False)
    result = _gate(repo)
    assert result.returncode != 0
    assert "unbindable" in result.stderr
    assert "gate_sources" in result.stderr


def test_multi_target_one_mismatched_bound_source_is_rejected(tmp_path: Path) -> None:
    repo = _make_multi_target_repo(tmp_path, with_gate_sources=True,
                                   mismatch_target="rtl/b.sv")
    result = _gate(repo)
    assert result.returncode != 0
    # proves per-target binding binds EACH: b fails even though a binds cleanly
    assert "rtl/b.sv" in result.stderr
    assert "bound source artifact" in result.stderr


def test_multi_target_fully_bound_is_accepted(tmp_path: Path) -> None:
    repo = _make_multi_target_repo(tmp_path, with_gate_sources=True)
    result = _gate(repo)
    assert result.returncode == 0, result.stderr
    assert "candidate patch is present in checkout" in result.stdout
    assert "1/1 receipts bound" in result.stdout
