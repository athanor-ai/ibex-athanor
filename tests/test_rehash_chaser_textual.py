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
