#!/usr/bin/env python3
"""ATH-3133 rehash-chaser: given changed files, find and update ALL hash bindings.

After a scrub changes file content (e.g. replacing internal paths), every
SHA256SUMS and manifest.json that transitively binds those files must be updated.
Three manual chases (ibex #54, openc910 #74, cv32e40p #20) proved this is a
multi-layer problem:

  1. Package-local SHA256SUMS (same dir, entries like ``./file.log`` or ``file.log``)
  2. Parent-level SHA256SUMS (parent dir, entries like ``./subdir/file.log``)
  3. Frontier manifests (``athanor/ppa_frontier/*/manifest.json`` binding via
     relative ``../../../athanor_artifacts/...`` paths with SHA256 fields)

This tool automates the chase so the fourth scrub is the last manual one.

Usage:
    python3 athanor/rehash_chaser.py <changed-file> [<changed-file> ...]
    python3 athanor/rehash_chaser.py --from-git   # chase all files changed vs origin/master
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _find_all_sums(repo: Path) -> list[Path]:
    return sorted(repo.rglob("SHA256SUMS"))


def _find_all_manifests(repo: Path) -> list[Path]:
    return sorted(repo.glob("athanor/ppa_frontier/*/manifest.json"))


def _read_exact(path: Path) -> str:
    """Read WITHOUT universal-newline translation.

    ``Path.read_text`` silently converts CRLF to LF on read, so carriage
    returns are gone before any edit happens and cannot be written back. On a
    surface whose whole claim is "these bytes hash to this value", any
    transformation that preserves MEANING while changing BYTES is the bug --
    which is the defect this tool exists to fix, so it must not use a call
    that commits it. (dexter, ibex #62: a real CRLF manifest reported
    "rehashed" while its CRLF count went 8 -> 0.)
    """
    with open(path, "r", encoding="utf-8", newline="") as fh:
        return fh.read()


def _write_exact(path: Path, text: str) -> None:
    """Write WITHOUT newline translation. See _read_exact."""
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def _plan_rehash(repo: Path, changed_files: list[Path]):
    """PHASE 1 -- PLAN. Compute every edit across every file and layer, and
    touch nothing on disk.

    Returns (plans, failures) where plans is {path: (new_text, [receipts])}.

    Edits are grouped BY TARGET PATH before being applied, so two changed
    files that both bind into one SHA256SUMS produce one coherent edit of that
    file rather than two edits each computed against the original text.
    """
    all_sums = _find_all_sums(repo)
    all_manifests = _find_all_manifests(repo)

    # path -> (is_json, [(old_sha, new_sha)], [receipt lines])
    pending: dict[Path, tuple[bool, list, list]] = {}

    def _note(path: Path, is_json: bool, old: str, new: str, receipt: str) -> None:
        entry = pending.setdefault(path, (is_json, [], []))
        entry[1].append((old, new))
        entry[2].append(receipt)

    for changed in changed_files:
        if not changed.is_file():
            continue
        new_hash = _sha256_file(changed)

        for sums_path in all_sums:
            sums_dir = sums_path.parent
            for line in _read_exact(sums_path).splitlines():
                if not line.strip() or line.startswith("#"):
                    continue
                parts = line.split("  ", 1)
                if len(parts) != 2:
                    continue
                old_hash, ref_path = parts
                ref_path = ref_path.rstrip("\r")
                candidate = sums_dir / ref_path
                if not candidate.is_file():
                    candidate = repo / ref_path
                try:
                    if candidate.resolve() == changed.resolve() and old_hash != new_hash:
                        _note(sums_path, False, old_hash, new_hash,
                              f"rehashed {ref_path} in {sums_path.relative_to(repo)}")
                except (OSError, ValueError):
                    continue

        for manifest_path in all_manifests:
            manifest_dir = manifest_path.parent
            try:
                data = json.loads(_read_exact(manifest_path))
            except (json.JSONDecodeError, OSError):
                continue
            for section in data.values():
                if not isinstance(section, dict):
                    continue
                for _key, entry in section.items():
                    if not isinstance(entry, dict) or "sha256" not in entry or "path" not in entry:
                        continue
                    ref = manifest_dir / entry["path"]
                    try:
                        if ref.resolve() == changed.resolve():
                            actual = _sha256_file(ref)
                            if entry["sha256"] != actual:
                                _note(manifest_path, True, entry["sha256"], actual,
                                      f"manifest rehashed {entry['path']} in "
                                      f"{manifest_path.relative_to(repo)}")
                    except (OSError, ValueError):
                        continue

    plans: dict[Path, tuple[str, list]] = {}
    failures: list[str] = []
    for path, (is_json, edits, receipts) in sorted(pending.items()):
        text = _read_exact(path)
        edited, fails = _apply_hash_edits_textually(text, edits, quoted=is_json)
        if fails:
            failures.extend(f"{path.relative_to(repo)}: {f}" for f in fails)
            continue
        plans[path] = (edited, receipts)
    return plans, failures


def chase_and_rehash(repo: Path, changed_files: list[Path]):
    """Update every hash binding for ``changed_files``. ALL OR NOTHING.

    Returns (updates, failures) -- both lists of human-readable lines.

    TWO-PHASE, and the phases are the point (dexter, ibex #62). All-or-nothing
    guarding a single helper call is not all-or-nothing across an INVOCATION:
    a two-file chain used to write the first file, refuse the second, and
    leave published evidence half-updated. No hash collision is required for
    that -- identical content at different times is enough, so the trigger is
    ordinary rather than adversarial.

    ON HASH-BOUND PUBLISHED EVIDENCE A PARTIAL WRITE IS WORSE THAN A REFUSAL.
    A refusal leaves a tree that still verifies. A half-updated chain leaves
    one that verifies against nothing.

    So: PLAN every edit across every file and layer, REFUSE BEFORE ANY WRITE
    if any one of them cannot bind, and only then COMMIT.
    """
    plans, failures = _plan_rehash(repo, changed_files)
    if failures:
        return [], failures  # nothing written

    updates: list[str] = []
    for path, (text, receipts) in sorted(plans.items()):
        _write_exact(path, text)
        updates.extend(receipts)
    return updates, failures


def _apply_hash_edits_textually(text: str, edits: list[tuple[str, str]], quoted: bool = True):
    """Replace each (old_sha, new_sha) IN THE TEXT. Never re-serialise.

    ``quoted`` selects the needle: JSON manifests carry the hash inside double
    quotes, SHA256SUMS carries it bare. Both use the SAME occurrence-counting
    discipline, so neither can bind to the wrong entry.

    A JSON round-trip is an edit to EVERY BYTE of the file, not to the field
    you changed. ``json.dumps`` re-renders every value through Python's
    repr, so a published manifest carrying ``0.00000000454`` comes back as
    ``4.54e-09``: numerically equal, textually different, and the file is
    hash-bound evidence a customer can re-verify. A one-field edit that
    rewrites unrelated published values is a silent corruption of the record.

    (This is not hypothetical. It happened on a real scrub: ten receipts
    reformatted by a round-trip, caught only by diffing ONE file before
    trusting the batch. The fix then was the same as the fix here -- edit the
    text, and prove it with ``+N -0``.)

    AMBIGUITY IS REFUSED, NOT GUESSED. Two entries can legitimately carry the
    same sha256 (identical content at two paths). A blind string replace would
    rewrite both while the caller intended one, so when an old hash does not
    occur exactly once this returns a failure and the file is left untouched.
    Returns (new_text, failures).

    ALL OR NOTHING. On any failure the ORIGINAL text is returned, never a
    partially-edited one. Earlier this returned the text with the successful
    edits already applied alongside the failure list -- safe only because both
    callers happen to discard it on failure. A helper whose safety depends on
    caller discipline is a trap for the next caller, and "fail whole or do not
    fail" is the rule this tool exists to enforce on published evidence.

    That case is reachable, not theoretical: bob's chained-edit shape
    ``[(A,B), (B,C)]`` applies A->B, which makes B occur twice, so the second
    edit refuses -- leaving one edit applied in the returned string.
    """
    original = text
    failures: list[str] = []
    for old_sha, new_sha in edits:
        if old_sha == new_sha:
            continue
        needle = f'"{old_sha}"' if quoted else old_sha
        n = text.count(needle)
        if n != 1:
            failures.append(
                f"REFUSED: sha256 {old_sha[:12]} occurs {n} times in this file; "
                f"a textual edit cannot bind to one entry. Resolve by hand."
            )
            continue
        text = text.replace(needle, f'"{new_sha}"' if quoted else new_sha)
    if failures:
        return original, failures
    return text, failures


def _changed_files_from_git(repo: Path) -> list[Path]:
    """Get files changed vs origin/master (or origin/main)."""
    for base in ("origin/master", "origin/main"):
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", f"{base}...HEAD"],
                capture_output=True, text=True, cwd=repo, check=True,
            )
            return [repo / f for f in result.stdout.strip().splitlines()
                    if not f.endswith("SHA256SUMS") and not f.endswith("manifest.json")]
        except subprocess.CalledProcessError:
            continue
    return []


def main() -> int:
    repo = Path.cwd()
    if "--from-git" in sys.argv:
        changed = _changed_files_from_git(repo)
        if not changed:
            print("rehash-chaser: no changed files found vs origin/master or origin/main")
            return 0
    else:
        changed = [Path(f) for f in sys.argv[1:] if not f.startswith("-")]
        if not changed:
            print("usage: rehash_chaser.py <file> [<file> ...] | --from-git")
            return 2

    print(f"rehash-chaser: chasing {len(changed)} changed file(s)...")
    updates, failures = chase_and_rehash(repo, changed)

    # UPDATES AND FAILURES ARE STRUCTURALLY SEPARATE, so the summary cannot
    # count one as the other. The old code had a single `actions` list and
    # printed `len(actions)` as "binding(s) updated" -- on a refusal that
    # printed REFUSED twice and then claimed 2 bindings updated, at exit 0.
    # A refusal that exits zero and claims work is a receipt lying in three
    # directions at once. (dexter, ibex #62.)
    for f in failures:
        print(f"  {f}", file=sys.stderr)
    for u in updates:
        print(f"  {u}")

    if failures:
        print(
            f"rehash-chaser: REFUSED — {len(failures)} binding(s) could not be "
            f"bound; NOTHING was written. Resolve by hand.",
            file=sys.stderr,
        )
        return 1
    if updates:
        print(f"rehash-chaser: {len(updates)} binding(s) updated")
    else:
        print("rehash-chaser: no stale bindings found (all hashes current)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
