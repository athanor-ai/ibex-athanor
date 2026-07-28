"""Bites-tests for the inline hash-citation validator (ATH-3444).

Three classes, because a gate needs all three to be trustworthy:
  NECESSITY    it catches a stale citation, in the shape that actually shipped
  NARROWNESS   it stays silent on the many hash-shaped things in an RTL tree
  FAIL-CLOSED  an unreadable artifact is not a clean artifact
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from athanor import verify_hash_citations


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _packet(root: Path, files_map: dict[str, str] | None = None, **extra: Any) -> Path:
    package = root / "packet"
    package.mkdir(parents=True, exist_ok=True)
    (package / "COMMANDS.md").write_text("original\n", encoding="utf-8")
    doc: dict[str, Any] = {"files": files_map if files_map is not None
                           else {"COMMANDS.md": _sha(package / "COMMANDS.md")}}
    doc.update(extra)
    (package / "receipt.json").write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return package


def _problems(root: Path) -> list[str]:
    """Findings are selected by the word "citation" -- a finding phrased without
    it is invisible to its own consumer, so the selector is part of the contract."""
    return [p for p in verify_hash_citations.verify(root) if "citation" in p]


def test_a_correct_citation_is_silent(tmp_path: Path) -> None:
    _packet(tmp_path)
    assert _problems(tmp_path) == []


def test_stale_citation_is_caught(tmp_path: Path) -> None:
    """NECESSITY: manifest updated, citing artifact not -- the shape that shipped."""
    package = _packet(tmp_path)
    (package / "COMMANDS.md").write_text("edited later by another PR\n", encoding="utf-8")
    problems = _problems(tmp_path)
    assert any("STALE citation of COMMANDS.md" in p for p in problems), problems


def test_verilog_literals_are_not_citations(tmp_path: Path) -> None:
    """NARROWNESS: this tree is full of 64-char binary literals."""
    _packet(tmp_path, note="b" + "0" * 64)
    assert _problems(tmp_path) == []


def test_a_name_that_is_not_a_file_is_not_a_citation(tmp_path: Path) -> None:
    """NARROWNESS: only enumerated artifact extensions count as filenames."""
    _packet(tmp_path, **{"yosys_version": "a" * 64})
    assert _problems(tmp_path) == []


def test_citation_naming_an_absent_file_is_caught(tmp_path: Path) -> None:
    package = _packet(tmp_path)
    doc = json.loads((package / "receipt.json").read_text(encoding="utf-8"))
    doc["files"]["MISSING.md"] = "a" * 64
    (package / "receipt.json").write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    problems = _problems(tmp_path)
    assert any("not present" in p for p in problems), problems


def test_supersession_with_matching_current_is_accepted(tmp_path: Path) -> None:
    """Without this the live instance can never clear the gate."""
    package = _packet(tmp_path)
    original = _sha(package / "COMMANDS.md")
    (package / "COMMANDS.md").write_text("edited later\n", encoding="utf-8")
    doc = json.loads((package / "receipt.json").read_text(encoding="utf-8"))
    doc["files"]["COMMANDS.md"] = original
    doc["files_supersession"] = {"COMMANDS.md": {
        "current": _sha(package / "COMMANDS.md"),
        "superseded_by": "abc1234 (docs: rewrite commands)",
        "reason": "the file was changed after this artifact was written",
    }}
    (package / "receipt.json").write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    assert _problems(tmp_path) == []


def _superseded(tmp_path: Path, record: dict[str, Any]) -> list[str]:
    package = _packet(tmp_path)
    original = _sha(package / "COMMANDS.md")
    (package / "COMMANDS.md").write_text("edited later\n", encoding="utf-8")
    doc = json.loads((package / "receipt.json").read_text(encoding="utf-8"))
    doc["files"]["COMMANDS.md"] = original
    doc["files_supersession"] = {"COMMANDS.md": record}
    (package / "receipt.json").write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return _problems(tmp_path)


def test_ticket_or_pr_provenance_is_valid(tmp_path: Path) -> None:
    """A SELF-REFERENTIAL supersession cannot name its own commit SHA: the SHA does
    not exist until after the record is written. Name the most specific identifier
    that EXISTS at write time."""
    problems = _superseded(tmp_path, {
        "current": _sha(tmp_path / "packet" / "COMMANDS.md"),
        "superseded_by": "ATH-3444 (#62)",
        "reason": "internal handle scrubbed from this artifact",
    })
    assert problems == []


def test_blank_provenance_fails_closed(tmp_path: Path) -> None:
    """Accepting ticket form must not degrade into accepting anything: "   " is truthy."""
    for bad in ("", "   ", None, 42):
        problems = _superseded(tmp_path, {
            "current": _sha(tmp_path / "packet" / "COMMANDS.md"),
            "superseded_by": bad,
            "reason": "x",
        })
        assert any("missing superseded_by" in p for p in problems), (bad, problems)


def test_supersession_claiming_the_wrong_current_still_reds(tmp_path: Path) -> None:
    """NARROWNESS: the remedy must not become the loophole."""
    problems = _superseded(tmp_path, {
        "current": "f" * 64,
        "superseded_by": "abc1234 (subject)",
        "reason": "x",
    })
    assert any("claims current" in p for p in problems), problems


def test_supersession_for_an_unchanged_citation_reds(tmp_path: Path) -> None:
    """Stale bookkeeping would rot into cover for a later real drift."""
    package = _packet(tmp_path)
    doc = json.loads((package / "receipt.json").read_text(encoding="utf-8"))
    doc["files_supersession"] = {"COMMANDS.md": {
        "current": _sha(package / "COMMANDS.md"),
        "superseded_by": "abc1234 (subject)",
        "reason": "x",
    }}
    (package / "receipt.json").write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    problems = _problems(tmp_path)
    assert any("supersession record claims it was superseded" in p for p in problems), problems


def test_unreadable_artifact_fails_closed(tmp_path: Path) -> None:
    package = _packet(tmp_path)
    (package / "broken.json").write_bytes(b'{"a": "\xff\xfe not utf-8"}')
    problems = verify_hash_citations.verify(tmp_path)
    assert any("could not read for citation check" in p for p in problems), problems


def test_absent_artifact_root_is_not_a_failure(tmp_path: Path) -> None:
    """Not-applicable is a different absence from could-not-read."""
    assert verify_hash_citations.verify(tmp_path / "nope") == []


def test_every_finding_says_citation(tmp_path: Path) -> None:
    """Force the convention rather than trusting it: callers select on this token,
    so a finding phrased without it is silently invisible."""
    package = _packet(tmp_path)
    (package / "COMMANDS.md").write_text("edited later\n", encoding="utf-8")
    findings = verify_hash_citations.verify(tmp_path)
    assert findings
    for finding in findings:
        assert "citation" in finding, f"finding is invisible to callers: {finding}"


def test_exit_codes_follow_the_repo_contract(tmp_path: Path) -> None:
    _packet(tmp_path)
    assert verify_hash_citations.main(["--artifact-root", str(tmp_path)]) == 0
    (tmp_path / "packet" / "COMMANDS.md").write_text("changed\n", encoding="utf-8")
    assert verify_hash_citations.main(["--artifact-root", str(tmp_path)]) == 1
