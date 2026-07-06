#!/usr/bin/env python3
"""Classify whether an Ibex PR must run hosted OSS-FV.

The classifier is intentionally conservative.  Only project-front documentation
can take the lightweight status path; every design, verification, toolchain,
workflow, artifact, or unknown path requires the formal runner.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import PurePosixPath


DOC_ONLY_FILES = {
    "README.md",
    "CONTRIBUTING.md",
    "CREDITS.md",
    "LICENSE",
}


def is_doc_only_path(path: str) -> bool:
    path_obj = PurePosixPath(path)
    if not path_obj.parts or path_obj.is_absolute() or ".." in path_obj.parts:
        return False

    normalized = str(path_obj)
    if normalized in DOC_ONLY_FILES:
        return True
    return normalized.startswith("doc/")


def changed_files_from_git(base: str) -> list[str]:
    proc = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...HEAD"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return [line for line in proc.stdout.splitlines() if line.strip()]


def classify(paths: list[str]) -> tuple[bool, str]:
    if not paths:
        return True, "no changed files reported; requiring OSS-FV fail-closed"

    unsafe = [path for path in paths if not is_doc_only_path(path)]
    if unsafe:
        sample = ", ".join(unsafe[:5])
        suffix = "" if len(unsafe) <= 5 else f", ... ({len(unsafe)} unsafe paths)"
        return True, f"OSS-FV required by non-doc path(s): {sample}{suffix}"

    sample = ", ".join(paths[:5])
    suffix = "" if len(paths) <= 5 else f", ... ({len(paths)} doc paths)"
    return False, f"docs-only change set: {sample}{suffix}"


def write_output(path: str, pairs: dict[str, str]) -> None:
    with open(path, "a", encoding="utf-8") as handle:
        for key, value in pairs.items():
            handle.write(f"{key}={value}\n")


def emit_result(requires_oss_fv: bool, reason: str, github_output: str | None) -> None:
    runner_labels = (
        '["self-hosted","Linux","X64"]' if requires_oss_fv else '["ubuntu-22.04"]'
    )
    pairs = {
        "requires_oss_fv": "true" if requires_oss_fv else "false",
        "runner_labels": runner_labels,
        "summary": reason,
    }
    for key, value in pairs.items():
        print(f"{key}={value}")
    if github_output:
        write_output(github_output, pairs)


def run_selftest() -> None:
    cases = [
        (["README.md"], False),
        (["doc/02_user/integration.rst"], False),
        (["README.md", "doc/01_overview/index.rst"], False),
        (["Doc/readme.md"], True),
        (["DOC/x.rst"], True),
        (["readme.md"], True),
        (["docs/overview.md"], True),
        (["doc"], True),
        (["doc/../rtl/ibex_if_stage.sv"], True),
        (["rtl/ibex_if_stage.sv"], True),
        (["rtl/README.md"], True),
        (["README.md", "rtl/ibex_if_stage.sv"], True),
        (["dv/formal/README.md"], True),
        (["formal/icache/README.md"], True),
        (["nix/syn.nix"], True),
        ([".github/workflows/ci-formal.yml"], True),
        (["athanor_artifacts/foo/top_level_first_receipt.json"], True),
        (["ci/oss_fv_scope.py"], True),
        (["unknown/path.txt"], True),
    ]
    for paths, expected in cases:
        actual, reason = classify(paths)
        if actual != expected:
            joined = ", ".join(paths)
            raise AssertionError(
                f"classify({joined}) got requires={actual}, expected {expected}: {reason}"
            )
    print(f"selftest passed ({len(cases)} cases)")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", help="Git base revision for PR diff classification")
    parser.add_argument("--changed-file", action="append", default=[])
    parser.add_argument("--github-output")
    parser.add_argument("--require", action="store_true")
    parser.add_argument("--reason", default="non-PR event requires OSS-FV")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)

    if args.selftest:
        run_selftest()
        return 0

    if args.require:
        emit_result(True, args.reason, args.github_output)
        return 0

    paths = args.changed_file
    if args.base:
        paths.extend(changed_files_from_git(args.base))

    requires_oss_fv, reason = classify(paths)
    emit_result(requires_oss_fv, reason, args.github_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
