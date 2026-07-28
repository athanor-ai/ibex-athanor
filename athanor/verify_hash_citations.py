#!/usr/bin/env python3
"""Verify that hashes quoted INLINE inside published artifacts are still true.

SHA256SUMS proves a manifest matches file CONTENT. It says nothing about the
hashes an artifact quotes inline, e.g. a receipt's ``"files"`` map. So a change
that edits a file, updates SHA256SUMS, and misses a citing artifact passes every
existing check -- and did: this validator lands red against a live citation on
this fork, and its twin found 13 on openc910 (ATH-3444).

NARROWNESS IS THE DESIGN CONSTRAINT. This is an RTL tree, so a rule like "every
64-hex token must be a known hash" reds every .v file -- Verilog binary literals
are routinely 40 or 64 characters of [01]. The enforced rule is NAME-BOUND: a
JSON entry mapping a FILENAME to a 64-hex value must equal that file's current
content. Nothing else is enforced by hash value.

SUPERSESSION is the remedy for a citation whose file legitimately changed later.
A receipt's citation is a HISTORICAL claim -- "I verified this, and here is the
content that accompanied the claim." Rewriting it to the current hash would make
the artifact assert something about a file version that did not exist when it
was written. So the original stays primary and the current hash is additive:

    "files": { "COMMANDS.md": "<original>" },
    "files_supersession": {
      "COMMANDS.md": {
        "current":       "<current>",
        "superseded_by": "abc1234 (subject)" or "ATH-3444 (#62)",
        "reason":        "why the file changed after this artifact was written"
      }
    }

``superseded_by`` accepts a ticket/PR reference as well as a commit SHA: a
SELF-REFERENTIAL supersession (the change that supersedes a citation is the very
commit being written) cannot name its own SHA. The rule is to name the most
specific identifier that EXISTS at write time.

Exit codes follow the repo-wide contract:
    0  ran, clean
    1  ran, found something
    2  COULD NOT RUN (tool defect)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = REPO_ROOT / "athanor_artifacts"

EXIT_CLEAN = 0
EXIT_FOUND = 1
EXIT_TOOL_ERROR = 2

# A filename key mapped to a 64-hex value. Extensions are enumerated so prose
# keys and version strings cannot be mistaken for filenames.
CITATION = re.compile(
    r'"(?P<name>[A-Za-z0-9_][A-Za-z0-9_.-]*'
    r'\.(?:md|json|v|sv|sh|log|txt|h|vcd))"\s*:\s*"(?P<sha>[0-9a-f]{64})"'
)
SUPERSESSION_REQUIRED = ("current", "superseded_by", "reason")


class ToolError(Exception):
    """The check could not be run. Never reported as clean."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _supersession_records(doc: object) -> dict[str, dict]:
    """Collect ``<key>_supersession`` maps of ``name -> record`` anywhere in a doc."""
    found: dict[str, dict] = {}

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key.endswith("_supersession") and isinstance(value, dict):
                    for name, record in value.items():
                        if isinstance(record, dict):
                            found[name] = record
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(doc)
    return found


def verify(root: Path = ARTIFACT_ROOT) -> list[str]:
    """Return citation problems. Every finding contains the word "citation".

    Callers select findings by that token, so a finding phrased without it would
    be invisible to its own consumer -- a check reporting into a void. A test
    asserts the property rather than trusting each message.
    """
    problems: list[str] = []
    if not root.is_dir():
        # A fork with no published artifacts yet is not a failure. This is
        # not-applicable, which is a different absence from could-not-read.
        return problems
    for path in sorted(root.rglob("*.json")):
        rel = path.relative_to(REPO_ROOT)
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            # Fail closed: an unreadable artifact is not a clean artifact.
            problems.append(f"{rel}: could not read for citation check ({exc})")
            continue
        try:
            supersessions = _supersession_records(json.loads(text))
        except json.JSONDecodeError:
            supersessions = {}
        for lineno, line in enumerate(text.splitlines(), 1):
            for match in CITATION.finditer(line):
                name, sha = match.group("name"), match.group("sha")
                target = (path.parent / name).resolve()
                try:
                    target.relative_to(root.resolve())
                except ValueError:
                    problems.append(
                        f"{rel}:{lineno}: citation of {name} escapes the artifact root"
                    )
                    continue
                if not target.is_file():
                    problems.append(
                        f"{rel}:{lineno}: citation names {name}, which is not present"
                    )
                    continue
                got = _sha256(target)
                record = supersessions.get(name)
                if got == sha:
                    if record is not None:
                        problems.append(
                            f"{rel}:{lineno}: citation of {name} matches the file, but a "
                            f"supersession record claims it was superseded"
                        )
                    continue
                if record is None:
                    problems.append(
                        f"{rel}:{lineno}: STALE citation of {name}: "
                        f"artifact says {sha}, file is {got}"
                    )
                    continue
                # Whitespace-only is not provenance: "   " is truthy, so a bare
                # falsy check would accept it.
                missing = [
                    field
                    for field in SUPERSESSION_REQUIRED
                    if not isinstance(record.get(field), str) or not record[field].strip()
                ]
                if missing:
                    problems.append(
                        f"{rel}:{lineno}: supersession record for the {name} citation "
                        f"is missing {', '.join(missing)} -- a supersession must say "
                        f"what changed it and why"
                    )
                elif record["current"] != got:
                    # The remedy must not become the loophole.
                    problems.append(
                        f"{rel}:{lineno}: supersession for the {name} citation claims "
                        f"current {record['current']}, file is {got}"
                    )
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", type=Path, default=ARTIFACT_ROOT)
    args = parser.parse_args(argv)
    try:
        problems = verify(args.artifact_root)
    except ToolError as exc:
        print(f"TOOL ERROR: {exc}", file=sys.stderr)
        return EXIT_TOOL_ERROR
    if problems:
        for problem in problems:
            print(f"FAIL: {problem}", file=sys.stderr)
        return EXIT_FOUND
    print(f"OK: inline hash citations verified under {args.artifact_root}")
    return EXIT_CLEAN


if __name__ == "__main__":
    sys.exit(main())
