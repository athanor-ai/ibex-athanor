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


def chase_and_rehash(repo: Path, changed_files: list[Path]) -> list[str]:
    """Find every SHA256SUMS/manifest entry binding a changed file and update it.

    Returns a list of human-readable actions taken (for receipts)."""
    actions: list[str] = []
    all_sums = _find_all_sums(repo)
    all_manifests = _find_all_manifests(repo)

    for changed in changed_files:
        if not changed.is_file():
            continue
        new_hash = _sha256_file(changed)
        basename = changed.name

        # Layer 1+2: SHA256SUMS files (any that reference this file by any path form)
        for sums_path in all_sums:
            sums_dir = sums_path.parent
            # newline="" DISABLES universal-newline translation. Path.read_text
            # silently converts CRLF to LF on READ, so the carriage returns are
            # gone before any edit happens and writing them back is impossible.
            # A byte-preserving edit has to disable translation on BOTH sides.
            with open(sums_path, "r", encoding="utf-8", newline="") as _fh:
                sums_text = _fh.read()
            # SAME DISCIPLINE AS THE MANIFEST LAYER: splitlines() to FIND, then
            # edit the ORIGINAL TEXT to write. The old code rebuilt the file
            # with "\n".join(new_lines) + "\n", which is a re-render, not an
            # edit -- it silently normalised CRLF to LF (every line loses its
            # carriage return) and added a trailing newline where the file had
            # none. Both are byte changes on hash-bound evidence, which is the
            # exact class this change exists to stop, in the same function.
            # (quan, ibex #62, executed: CRLF 1->0 and trailing-newline
            # False->True on a one-hash edit.)
            sums_pending: list[tuple[str, str]] = []
            sums_found: list[str] = []
            for line in sums_text.splitlines():
                if not line.strip() or line.startswith("#"):
                    continue
                parts = line.split("  ", 1)
                if len(parts) != 2:
                    continue
                old_hash, ref_path = parts
                ref_path = ref_path.rstrip("\r")  # tolerate CRLF when RESOLVING
                candidate = sums_dir / ref_path
                if not candidate.is_file():
                    candidate = repo / ref_path
                try:
                    if candidate.resolve() == changed.resolve() and old_hash != new_hash:
                        sums_pending.append((old_hash, new_hash))
                        sums_found.append(
                            f"rehashed {ref_path} in {sums_path.relative_to(repo)}"
                        )
                except (OSError, ValueError):
                    continue
            if sums_pending:
                edited, failures = _apply_hash_edits_textually(
                    sums_text, sums_pending, quoted=False
                )
                if failures:
                    actions.extend(failures)
                    continue
                with open(sums_path, "w", encoding="utf-8", newline="") as _fh:
                    _fh.write(edited)
                actions.extend(sums_found)

        # Layer 3: frontier manifests (JSON with sha256 fields + relative paths)
        for manifest_path in all_manifests:
            manifest_dir = manifest_path.parent
            try:
                data = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            # Parsing is fine for FINDING which entries need a new hash. It is
            # writing back a parsed structure that destroys the file. So the
            # parse produces a list of (old, new) pairs and nothing else; the
            # edit itself is applied to the original TEXT below.
            # THE RECEIPT IS WRITTEN AFTER THE WRITE, NEVER DURING THE FIND.
            # An earlier version appended "manifest rehashed X" here, in the
            # discovery loop -- so on the REFUSAL path, where the file is
            # deliberately left untouched, the returned receipt still claimed
            # the rehash. A receipt that reports work the refusal prevented is
            # the same overclaim class this tool exists to protect against,
            # inside the tool. (bob, ibex #62.)
            pending: list[tuple[str, str]] = []
            found: list[str] = []
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
                                pending.append((entry["sha256"], actual))
                                found.append(
                                    f"manifest rehashed {entry['path']} in "
                                    f"{manifest_path.relative_to(repo)}"
                                )
                    except (OSError, ValueError):
                        continue
            if pending:
                text = manifest_path.read_text(encoding="utf-8")
                text, failures = _apply_hash_edits_textually(text, pending)
                if failures:
                    # Refused: report ONLY the refusal. `found` is discarded --
                    # nothing was written, so nothing may be claimed.
                    actions.extend(failures)
                    continue
                manifest_path.write_text(text, encoding="utf-8")
                actions.extend(found)

    return actions


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
    """
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
    actions = chase_and_rehash(repo, changed)
    if actions:
        for a in actions:
            print(f"  {a}")
        print(f"rehash-chaser: {len(actions)} binding(s) updated")
    else:
        print("rehash-chaser: no stale bindings found (all hashes current)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
