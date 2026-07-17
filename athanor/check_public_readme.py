#!/usr/bin/env python3
"""Check the public root README stays compact and customer-facing."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
MAX_LINES = 90
EXPECTED_TITLE = "# Athanor Ibex Results"
REQUIRED_SECTIONS = [
    "## Status",
    "## Promoted Evidence",
    "## Evidence Ledger",
    "## Evidence Bar",
    "## Replay",
    "## Upstream",
]
BANNED_PHRASES = [
    "Evidence Surface",
    "Current read",
    "TODO",
    "Awaiting",
    "Next Ambitious",
    "Proof Artifacts Awaiting",
    "Gaps And Next Work",
    "LLM",
    "slop",
    "roadmap",
    "still need",
    "active exploration",
    "How This",
    "How To",
]


def _fail(message: str) -> None:
    raise SystemExit(f"{README.relative_to(ROOT)}: {message}")


def main() -> int:
    text = README.read_text(encoding="utf-8")
    lines = text.splitlines()
    if len(lines) > MAX_LINES:
        _fail(f"too long for front-page reader path ({len(lines)} > {MAX_LINES})")
    if not lines or lines[0] != EXPECTED_TITLE:
        _fail(f"expected title {EXPECTED_TITLE!r}")

    cursor = -1
    for section in REQUIRED_SECTIONS:
        try:
            index = lines.index(section)
        except ValueError:
            _fail(f"missing section {section!r}")
        if index <= cursor:
            _fail(f"section {section!r} is out of order")
        cursor = index

    lowered = text.lower()
    for phrase in BANNED_PHRASES:
        if phrase.lower() in lowered:
            _fail(f"public README contains stale/internal phrase {phrase!r}")

    for match in re.finditer(r"\]\((athanor_artifacts/[^)]+)\)", text):
        target = ROOT / match.group(1)
        if not target.exists():
            _fail(f"artifact link target does not exist: {match.group(1)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
