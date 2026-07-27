"""Pin scope-neutral labels for the three ATH-3415 archival path fields."""

import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
EXPECTED_PATHS = (
    (
        "athanor/configs/ath2686_cv32e40p_common_guard_profile.json",
        "bounded_profile",
        "<local-tmp>/ath2686-cv32e40p-common-guard",
    ),
    (
        "athanor/configs/ath2686_cv32e40p_recon.json",
        "bounded_frontend_receipt",
        "<local-tmp>/ath2686-cv32e40p-recon",
    ),
    (
        "athanor/configs/ath2686_cv32e40p_regfile_guard_profile.json",
        "bounded_profile",
        "<local-tmp>/ath2686-cv32e40p-regfile-guard-y66",
    ),
)


@pytest.mark.parametrize(("relative_path", "section", "expected"), EXPECTED_PATHS)
def test_archival_artifact_path_is_scope_neutral(
    relative_path: str, section: str, expected: str
) -> None:
    receipt = json.loads((REPO_ROOT / relative_path).read_text(encoding="utf-8"))

    assert receipt[section]["local_artifact_dir"] == expected
