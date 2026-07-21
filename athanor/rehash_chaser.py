#!/usr/bin/env python3
"""ATH-3133 rehash-chaser: given changed files, find and update ALL hash bindings.

After a scrub changes file content (e.g. replacing /workdir or /tmp paths), every
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
            lines = sums_path.read_text(encoding="utf-8").splitlines()
            updated = False
            new_lines = []
            for line in lines:
                if not line.strip() or line.startswith("#"):
                    new_lines.append(line)
                    continue
                parts = line.split("  ", 1)
                if len(parts) != 2:
                    new_lines.append(line)
                    continue
                old_hash, ref_path = parts
                # resolve the ref_path to an actual file
                candidate = sums_dir / ref_path
                if not candidate.is_file():
                    candidate = repo / ref_path
                try:
                    if candidate.resolve() == changed.resolve():
                        if old_hash != new_hash:
                            new_lines.append(f"{new_hash}  {ref_path}")
                            actions.append(f"rehashed {ref_path} in {sums_path.relative_to(repo)}")
                            updated = True
                        else:
                            new_lines.append(line)
                    else:
                        new_lines.append(line)
                except (OSError, ValueError):
                    new_lines.append(line)
            if updated:
                sums_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

        # Layer 3: frontier manifests (JSON with sha256 fields + relative paths)
        for manifest_path in all_manifests:
            manifest_dir = manifest_path.parent
            try:
                data = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            updated = False
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
                                entry["sha256"] = actual
                                actions.append(
                                    f"manifest rehashed {entry['path']} in "
                                    f"{manifest_path.relative_to(repo)}"
                                )
                                updated = True
                    except (OSError, ValueError):
                        continue
            if updated:
                manifest_path.write_text(
                    json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )

    return actions


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
