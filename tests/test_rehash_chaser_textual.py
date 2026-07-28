"""rehash_chaser must EDIT published manifests, never RE-SERIALISE them (ATH-3133).

A JSON round-trip is an edit to every byte of the file, not to the field you
changed. ``json.dumps`` re-renders every value through Python's repr, so a
published manifest carrying ``0.00000000454`` comes back as ``4.54e-09`` --
numerically equal, textually different, and the manifest is hash-bound evidence
a customer re-verifies byte for byte.

This is not hypothetical: a real scrub reformatted ten published receipts
exactly this way, caught only by diffing ONE file before trusting the batch.

The append-only discipline that applies to published evidence gives the test
its shape: prove the edit is ``+N -0`` on everything except the target field.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_MOD = Path(__file__).resolve().parents[1] / "athanor" / "rehash_chaser.py"
_spec = importlib.util.spec_from_file_location("rehash_chaser", _MOD)
rc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rc)

# Values chosen because a round-trip DOES change them. If a future Python
# renders these identically the test would pass vacuously, so the round-trip
# control below asserts that it really does still corrupt them.
_MANIFEST = """{
  "frontier": {
    "cand1": {
      "path": "helper.log",
      "sha256": "OLDHASH",
      "power_w": 0.00000000454,
      "leakage_w": 1.2000000000000002e-11,
      "note": "unicode kept: \\u00b5W"
    }
  }
}
"""

_OLD = "a" * 64
_NEW = "b" * 64


def _manifest(old=_OLD):
    return _MANIFEST.replace("OLDHASH", old)


def test_the_round_trip_really_does_corrupt_these_values():
    """CONTROL for the test below. If json.dumps stopped reformatting these,
    the real test would pass for the wrong reason -- it would be asserting a
    property nothing threatens."""
    text = _manifest()
    data = json.loads(text)
    data["frontier"]["cand1"]["sha256"] = _NEW
    round_tripped = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    assert "0.00000000454" not in round_tripped, (
        "a round-trip no longer reformats this value; pick a value that still "
        "demonstrates the hazard or this suite proves nothing"
    )
    assert "4.54e-09" in round_tripped


def test_a_hash_edit_changes_only_the_hash_line():
    """THE INVARIANT: +1 -1, and every other byte identical."""
    before = _manifest()
    after, failures = rc._apply_hash_edits_textually(before, [(_OLD, _NEW)])
    assert failures == [], failures

    b, a = before.splitlines(), after.splitlines()
    assert len(b) == len(a), "line count changed; this was a re-render, not an edit"
    differing = [i for i, (x, y) in enumerate(zip(b, a)) if x != y]
    assert len(differing) == 1, (
        f"expected exactly one changed line, got {len(differing)}: "
        f"{[(b[i], a[i]) for i in differing]}"
    )
    assert _NEW in a[differing[0]] and "sha256" in a[differing[0]]

    # The values a round-trip would have eaten are byte-identical.
    for survivor in ("0.00000000454", "1.2000000000000002e-11", "\\u00b5W"):
        assert survivor in after, f"{survivor} did not survive the edit"


def test_two_entries_sharing_a_hash_are_refused_not_guessed():
    """AMBIGUITY IS REFUSED. Identical content at two paths legitimately shares
    a sha256; a blind string replace would rewrite both while the caller meant
    one. Refusing leaves the file untouched, which is recoverable -- guessing
    corrupts a second published entry, which is not."""
    doubled = _manifest() + _manifest()  # same hash twice
    after, failures = rc._apply_hash_edits_textually(doubled, [(_OLD, _NEW)])
    assert len(failures) == 1, failures
    assert "REFUSED" in failures[0] and "occurs 2 times" in failures[0]
    assert after == doubled, "the file was modified despite an ambiguous target"


def test_a_missing_hash_is_refused_too():
    """Zero occurrences is the same class as two: the edit cannot be bound.
    Silently succeeding here would report a rehash that never happened."""
    after, failures = rc._apply_hash_edits_textually(_manifest(), [("c" * 64, _NEW)])
    assert len(failures) == 1 and "occurs 0 times" in failures[0]
    assert after == _manifest()


def test_a_noop_edit_is_not_an_edit():
    """old == new must not count as a change or emit a failure."""
    after, failures = rc._apply_hash_edits_textually(_manifest(), [(_OLD, _OLD)])
    assert failures == []
    assert after == _manifest()


def _sums_repo(tmp_path, sums_bytes):
    """A package carrying a SHA256SUMS with the given EXACT bytes."""
    pkg = tmp_path / "athanor_artifacts" / "pkg"
    pkg.mkdir(parents=True)
    logfile = pkg / "helper.log"
    logfile.write_text("content\n", encoding="utf-8")
    (pkg / "SHA256SUMS").write_bytes(sums_bytes)
    return pkg / "SHA256SUMS", logfile


@pytest.mark.parametrize(
    "label, sums",
    [
        ("lf-with-trailing-newline", (_OLD + "  helper.log\n").encode()),
        ("crlf", (_OLD + "  helper.log\r\n").encode()),
        ("no-trailing-newline", (_OLD + "  helper.log").encode()),
        ("crlf-multiline", (_OLD + "  helper.log\r\n" + "b" * 64 + "  other.log\r\n").encode()),
        ("mixed-lf-and-crlf", (_OLD + "  helper.log\r\n" + "b" * 64 + "  other.log\n").encode()),
    ],
)
def test_the_sums_layer_changes_only_the_hash_bytes(tmp_path, label, sums):
    """THE SAME INVARIANT, THE OTHER LAYER. (quan, ibex #62.)

    The SHA256SUMS path rebuilt the file with ``"\\n".join(lines) + "\\n"``.
    That is a re-render, not an edit: it normalised CRLF to LF and added a
    trailing newline where the file had none -- byte changes on hash-bound
    evidence, which is the exact class the manifest layer was just fixed for,
    in the same function. The PR names SHA256SUMS in its own scope, so leaving
    it re-serialising would have been a fix that did not cover its own surface.

    ``Path.read_text`` performs universal-newline translation, so the carriage
    returns were gone before any edit could happen. Byte preservation needs
    translation disabled on BOTH the read and the write.
    """
    sums_path, logfile = _sums_repo(tmp_path, sums)
    before = sums_path.read_bytes()
    real_hash = rc._sha256_file(logfile)

    rc.chase_and_rehash(tmp_path, [logfile])

    after = sums_path.read_bytes()
    assert after == before.replace(_OLD.encode(), real_hash.encode()), (
        f"[{label}] the SHA256SUMS edit changed bytes other than the hash"
    )
    assert before.count(b"\r\n") == after.count(b"\r\n"), f"[{label}] CRLF normalised"
    assert before.endswith(b"\n") == after.endswith(b"\n"), (
        f"[{label}] trailing-newline state changed"
    )


def test_a_refused_edit_reports_no_rehash_it_did_not_perform(tmp_path):
    """THE RECEIPT MAY NOT CLAIM WORK THE REFUSAL PREVENTED. (bob, ibex #62.)

    The receipt line was appended in the DISCOVERY loop, before the edit was
    attempted. So on the refusal path -- where the file is deliberately left
    untouched -- the returned actions still said "manifest rehashed X". A
    receipt reporting a write that never happened is the overclaim class this
    tool exists to protect against, inside the tool.

    Discovery is not performance. The receipt is written after the write.
    """
    frontier = tmp_path / "athanor" / "ppa_frontier" / "cand1"
    frontier.mkdir(parents=True)
    logfile = frontier / "helper.log"
    logfile.write_text("synthesis log\n", encoding="utf-8")

    # Two entries carrying the SAME stale hash -> the edit cannot bind -> refused.
    manifest = frontier / "manifest.json"
    before = json.dumps({
        "frontier": {
            "a": {"path": "helper.log", "sha256": _OLD},
            "b": {"path": "helper.log", "sha256": _OLD},
        }
    }, indent=2) + "\n"
    manifest.write_text(before, encoding="utf-8")

    actions = rc.chase_and_rehash(tmp_path, [logfile])

    assert manifest.read_text(encoding="utf-8") == before, (
        "the file was modified on the refusal path"
    )
    assert any("REFUSED" in a for a in actions), actions
    assert not any("manifest rehashed" in a for a in actions), (
        "the receipt claimed a rehash that the refusal prevented: " + repr(actions)
    )


def test_the_real_entry_point_edits_a_manifest_on_disk_without_re_rendering(tmp_path):
    """DRIVES THE BINDING, not the helper.

    Every test above calls ``_apply_hash_edits_textually`` directly. That proves
    the helper is correct and proves NOTHING about whether ``chase_and_rehash``
    actually routes through it -- a fix that lives in the caller is invisible to
    a component-level probe, which is a defect I raised on someone else's PR an
    hour before writing this file.

    So this drives the shipped entry point against a real manifest on disk and
    asserts the same +1 -1 property on the bytes it leaves behind.
    """
    frontier = tmp_path / "athanor" / "ppa_frontier" / "cand1"
    frontier.mkdir(parents=True)
    logfile = frontier / "helper.log"
    logfile.write_text("synthesis log\n", encoding="utf-8")
    real_hash = rc._sha256_file(logfile)

    manifest = frontier / "manifest.json"
    before = _manifest(old=_OLD)          # a stale hash, so there is work to do
    manifest.write_text(before, encoding="utf-8")

    actions = rc.chase_and_rehash(tmp_path, [logfile])

    after = manifest.read_text(encoding="utf-8")
    assert any("manifest rehashed" in a for a in actions), actions

    b, a = before.splitlines(), after.splitlines()
    assert len(b) == len(a), "line count changed; the entry point re-rendered the file"
    differing = [i for i, (x, y) in enumerate(zip(b, a)) if x != y]
    assert len(differing) == 1, (
        f"expected exactly one changed line through the real entry point, got "
        f"{len(differing)}: {[(b[i], a[i]) for i in differing]}"
    )
    assert real_hash in a[differing[0]]

    for survivor in ("0.00000000454", "1.2000000000000002e-11", "\\u00b5W"):
        assert survivor in after, f"{survivor} did not survive the real entry point"
