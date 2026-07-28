#!/usr/bin/env python3
"""ATH-2960 fork export-safety gate for the public Athanor RTL forks.

This is a fail-closed CI gate for the public ``openc910-athanor`` /
``riscv-boom-athanor`` forks. It scans the **committed bytes** of every tracked
file at a ref (default ``HEAD``) via ``git ls-tree`` + ``git show <ref>:<path>``,
never the working tree, so locally generated artifacts -- in particular
``*.replay.log`` files, which embed the caller's pinned tool paths -- can neither
false-trip the gate nor let a real committed leak hide behind "it is only a
local file".

It scans BYTES, not ``git grep``, on purpose: the packages mark ``*.log`` /
``*.sv`` / ``*.v`` as ``binary`` in ``.gitattributes``, and ``git grep -I``
silently SKIPS binary files -- so a token or key inside a ``*.pinned.log`` (the
verbatim tool output where a real credential is likeliest to leak) would slip
past a git-grep scan. Reading committed bytes and matching directly closes that
gap regardless of ``.gitattributes``. (ATH-2960, blind spot caught in review on
PR #4.)

Two tiers (customer-surface owner ruling, ATH-2960):

  BLOCK  hard-safety leaks; any committed-tree hit fails the gate:
           - internal absolute filesystem paths and home directories
           - tmp / tool-cache paths
           - the cloud build username
           - the internal ops-repo name
           - confidential customer names
           - secret tokens (GitHub, Slack, AWS, AI-provider API keys, private keys)
           - AI-tool / vendor authorship markers (the bot attribution footer)

  WARN   conscious-choice internal metadata; surfaced, never blocks:
           - internal Linear ticket IDs
           - the private Kairos-repo pointer
         These are not secrets or paths -- their exposure is a deliberate
         per-artifact choice and some is intentional/team-settled, so the gate
         reports them for a conscious keep/scrub decision rather than blocking.

It also runs the package receipt verifier (SHA256 manifest + ``receipt.json``
parse) and is fail-closed if that verifier is missing or errors.

The forbidden strings below are assembled from fragments so this gate's OWN
source never contains a verbatim forbidden literal -- otherwise it would
self-trip on every run. (The receipt verifier uses the same convention.)

Exit codes:
  0  clean (WARN findings allowed)
  1  a BLOCK leak was found, or the receipt verifier failed
  2  the gate itself could not run (not in a git repo, git missing, ...)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


# --- BLOCK tiers. Regexes are fragment-built so this file holds no verbatim leak.
#
# These forks are forks-OF-UPSTREAM (OpenC910, riscv-boom/FireSim). Upstream
# ships its OWN host paths in its OWN files (its CI references upstream home dirs
# and a FireSim temp instance-data file) -- that is public-upstream content, NOT
# our leak, and must not be flagged (scrubbing it would diverge the fork). So
# two tiers (patterns fragment-built so this file holds no verbatim leak string):
#
#   BLOCK_ALWAYS  our unambiguous internal markers + secrets. Never legitimate
#                 anywhere, in upstream or our files -> block across the whole tree.
#   BLOCK_SCOPED  ambiguous host paths. Our leak risk is a VM path landing in an
#                 artifact WE add; upstream's own host paths are fine. So block
#                 these ONLY under OUR_ADDED_PREFIXES.
BLOCK_ALWAYS: list[tuple[str, str]] = [
    ("internal workdir path", "/work" + "dir"),
    ("cloud build username", "azure" + "user"),
    ("internal ops repo", "athanor-" + "kairos-runall"),
    # Export-safety hardening (review): the internal project namespace used as a
    # schema or module PATH -- e.g. a receipt "schema": "<ns>.<ticket>..." or a
    # "from <ns>.sub import ..." line. A public fork has no legitimate reason to
    # carry an internal module/schema path (owner ruling: BLOCK, fail-closed; any
    # future legit case goes through the audited allowlist, not a weakened
    # pattern). The repo POINTER "athanor-<ns>" stays WARN below; the
    # (?<!athanor-) lookbehind keeps this BLOCK from reclassifying the pointer's
    # dotted forms. Fragment-built so this file holds no verbatim marker and does
    # not self-trip its own committed-tree scan.
    ("internal Kairos namespace", r"(?<!athanor-)" + "kai" + r"ros\.[A-Za-z_]"),
    ("confidential customer name", r"[Nn][Vv][Ii][Dd][Ii][Aa]"),
    ("confidential customer name", r"[Aa][Nn][Nn][Aa][Pp][Uu][Rr][Nn][Aa]"),
    # Export-safety hardening (review ruling 2026-07-15, ATH-2960 vendor-footer
    # class): AI-tool / vendor authorship markers. A bot's auto-generated
    # "Generated with <tool>" attribution footer -- and its "<vendor>.com"
    # co-author trailer -- is a public-surface tool/vendor-name reference on a
    # customer-facing RTL fork. Our public posture names only the VERDICT tools
    # (Yosys/OpenSTA/Lean, public by design); the proposal-side stack is
    # proprietary, and an AI-tool authorship footer leaks it. Owner ruling: BLOCK,
    # FORK-SCOPE only -- private-repo authorship trails are unchanged; the leak is
    # a vendor marker crossing the customer boundary, not its existence. One
    # SINGLE source of truth (BLOCK_ALWAYS) so the committed-tree scan AND
    # --scan-text (PR body / comments, where the footer actually lands) both
    # enforce it. Fragment-built + (?i) so this file holds no verbatim marker and
    # cannot self-trip its own committed-tree scan.
    ("AI-tool name", r"(?i)cla" + "ude"),
    ("AI-vendor name", r"(?i)anthro" + "pic"),
    ("AI-tool authorship footer", r"(?i)generated with \[?cla" + "ude"),
    ("GitHub token", r"gh[posru]_[A-Za-z0-9]{20,}"),
    ("GitHub fine-grained PAT", r"github_pat_[A-Za-z0-9_]{20,}"),
    ("Slack token", r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    ("AWS access key id", r"AKIA[0-9A-Z]{16}"),
    ("Anthro" "pic API key", r"sk-ant-[A-Za-z0-9_-]{20,}"),
    ("OpenAI API key", r"sk-[A-Za-z0-9]{20,}"),
    ("private key block", r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]
BLOCK_SCOPED: list[tuple[str, str]] = [
    ("home directory path", "/ho" + r"me/[A-Za-z0-9._-]+"),
    ("macOS home path", "/Use" + r"rs/[A-Za-z0-9._-]+"),
    ("tmp / tool-cache path", "/t" + r"mp/[A-Za-z0-9._/-]+"),
]
# Paths WE author on these forks; ambiguous host-path scanning is scoped to these.
OUR_ADDED_PREFIXES: tuple[str, ...] = (
    "athanor/",
    "athanor_artifacts/",
    "generated_rtl_capture/",
    "docs/customer/",
    "README.md",
)

# --- WARN tier: (label, extended-regex, exclude-regex-or-None). Never blocks.
WARN_PATTERNS: list[tuple[str, str, str | None]] = [
    # Case-insensitive + hyphen-optional (owner ruling: stays WARN): a producer
    # that emits "ath2852" (lowercase, no hyphen -- the natural machine form in a
    # schema/module segment) evaded the old case+hyphen-pinned "ATH-[0-9]{4}". The
    # leading \b keeps it off in-word digits like "datapath2960".
    ("internal Linear ticket id", r"(?i)\b" + "ath" + r"-?[0-9]{4}", None),
    # The private-repo pointer is WARN, but the internal ops-repo name is BLOCK;
    # exclude the ops-repo hits here so they are not double-reported as a warn.
    ("private Kairos-repo pointer", "athanor-" + "kairos", "athanor-" + "kairos-runall"),
]


# --- SPAN-BOUND EXEMPTIONS (review verdict on ibex #53, 2026-07-21).
#
# Each exemption is (label_set, path_predicate, line_predicate). A BLOCK hit is
# suppressed ONLY when its label matches label_set, its file path matches the
# path predicate, AND the matched line matches the line predicate. The line
# predicate prevents a blanket directory exemption from also hiding secrets,
# credentials, or internal paths that happen to land in the same subtree.
#
# Fragment-built so this file holds no verbatim forbidden literal.

_ABLATION_PREFIX = "athanor_artifacts/ibex_fetch_fifo_native_agent_ablation/"
_ABLATION_AI_LABELS = frozenset({"AI-tool name", "AI-vendor name", "AI-tool authorship footer"})

_CONVENTION_ID = "kai" + "ros.ibex.toggle.control_path.v1"
_CONVENTION_EXACT_PREFIXES = (
    "athanor/toolchain_policy.json",
    "athanor_artifacts/if_stage_expanded_predicate_factor/",
    "athanor_artifacts/if_stage_no_bp_prefetch_direct/",
)

SPAN_EXEMPTIONS: list[tuple[frozenset[str], tuple[str, ...], bytes | None]] = [
    # 1. AI-methodology ablation: AI-tool/vendor terms inside this subtree are
    #    evidence (native-agent-vs-Kairos ablation), not leaked authorship.
    (_ABLATION_AI_LABELS, (_ABLATION_PREFIX,), None),
    # 2. Convention replay ID: exact convention ID at exact replay paths.
    (frozenset({"internal Kairos namespace"}), _CONVENTION_EXACT_PREFIXES,
     _CONVENTION_ID.encode()),
]


class GateError(RuntimeError):
    """The gate could not run (distinct from a leak verdict)."""


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def _repo_root(start: Path) -> Path:
    proc = _git(["rev-parse", "--show-toplevel"], start)
    if proc.returncode != 0:
        raise GateError(f"not a git repository at {start}: {proc.stderr.strip()}")
    return Path(proc.stdout.strip())


# BINARY IS A PROPERTY OF THE BYTES, NOT OF THE NAME. This was an extension list,
# which is the same defect as the handle scan's own allow-list one layer down: an
# ASCII file named .bin was skipped on its name while its contents were perfectly
# scannable. A NUL byte decides, and nothing else. Skips are REPORTED with a
# reason, never silent.


def _committed_paths(ref: str, root: Path) -> list[str]:
    """All file paths tracked at ``ref`` (committed tree; untracked excluded)."""
    proc = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", "-z", ref],
        cwd=root, capture_output=True,
    )
    if proc.returncode != 0:
        raise GateError(f"git ls-tree failed at {ref}: {proc.stderr.decode(errors='replace').strip()}")
    return [p.decode("utf-8", "surrogateescape") for p in proc.stdout.split(b"\0") if p]


def _committed_bytes(ref: str, path: str, root: Path) -> bytes:
    """The committed bytes of ``path`` at ``ref`` (never the working tree)."""
    proc = subprocess.run(["git", "show", f"{ref}:{path}"], cwd=root, capture_output=True)
    if proc.returncode != 0:
        raise GateError(f"git show failed for {path} at {ref}: {proc.stderr.decode(errors='replace').strip()}")
    return proc.stdout


def _is_exempt(label: str, path: str, line: bytes) -> bool:
    """Check span-bound exemptions: label + path + optional line predicate."""
    for labels, path_prefixes, line_needle in SPAN_EXEMPTIONS:
        if label not in labels:
            continue
        if not path.startswith(path_prefixes):
            continue
        if line_needle is not None and line_needle not in line:
            continue
        return True
    return False


# --- Fleet-agent handle denylist (ATH-3397).
#
# Internal fleet-agent handles must not appear in published customer artifacts on
# a public fork. The handle list is GENERATED from the roster SSOT (ATH-1343
# roles.json) by athanor/gen_fleet_handle_denylist.py -- never hardcoded here, so
# this gate's source holds no verbatim handle and cannot self-flag on its own scan
# (the same fragment discipline the BLOCK lists use). The denylist DATA file
# necessarily DOES hold the handles verbatim, so it is the one path excluded from
# the handle scan (below).
DENYLIST_REL = "athanor/fleet_handle_denylist.json"

# Truncation tripwire for the generated denylist (see _load_agent_handles).
MIN_HANDLES = 8

# The handle scan targets PUBLISHED CUSTOMER-ARTIFACT PROSE (ATH-3397): receipt /
# certificate / README text a customer reads. Two deliberate boundaries:
#
#  * Positive file scope: only these artifact extensions are scanned for handles.
#    A handle inside a build/replay LOG PATH (e.g. .log / .patch) is a DIFFERENT
#    class -- named per-agent scratch dirs -- fixed at the producer (neutral
#    paths + regenerate), never by editing the published log, which would break
#    the reproducibility the packet exists to offer. Tracked as ATH-3415.
#  * Enumerated path exemptions (NOT an extension rule): specific tooling files
#    that are themselves .json/.md but are infra, not a customer surface. Each
#    carries its reason so adding one is a visible decision, never a side effect.
#    (The fork's tooling .py/.sh source is out of scope by the positive extension
#    scope above -- attribution comments there are ordinary contributor bylines.)
# ATH-3397 TIER STAGING (asabi ruling, openc910 fork-asymmetry): on a fork where
# `export-safety` is a REQUIRED status context, a gate that reds by design can
# never merge the PR that introduces it. So the handle scan lands at WARN — the
# gate runs, NAMES every live instance in the log, and leaves the required
# context green — then is PROMOTED to BLOCK after the scrub lands.
#
# The promotion is proven by EXERCISE, never inherited from WARN: by promotion
# time the real population is zero, so a BLOCK tier that has never blocked
# anything would look identical to one that cannot. See
# test_block_tier_exits_nonzero_on_a_constructed_instance.
HANDLE_FINDING_TIER = "warn"  # "warn" (staging) | "block" (enforcing)
# NOTE the fork asymmetry: ibex master has NO required status checks, so this
# gate lands ENFORCING and red-by-design against its live population, which is
# the land-red-first evidence. openc910 requires export-safety, so its twin
# stages at "warn" and is promoted after the scrub. Same code, different default,
# and the difference is the ruleset rather than a judgement.

# SCOPE IS DERIVED, NOT ENUMERATED (ported from the openc910 twin, #83 / 8edc85eb9).
# This was an extension allow-list of (".json", ".md"), and it was declared TWICE
# in this module -- the second shadowing the first, so editing the visible one
# would have changed nothing. On the twin the same list inspected 15% of published
# artifacts and reported clean over the rest. A derived byte probe finds live
# handle rows in 14 files outside that scope here, including published logs and
# a patch header.
#
# Every committed TEXT file under our authored prefixes is scanned, and anything
# skipped is named here WITH ITS REASON, so an unknown or new file type is LOUD
# rather than silently out of scope. Binary is decided by a NUL byte -- a
# property of the bytes, not a guess from the name.
HANDLE_SCAN_EXEMPT_PATHS: dict[str, str] = {
    DENYLIST_REL: "the denylist DATA file; holds every handle verbatim by design",
    "athanor/export_safety_gate.py":
        "this gate; a detector necessarily contains the thing it detects, and "
        "scrubbing it would disable the protection",
    "athanor/gen_fleet_handle_denylist.py":
        "the denylist GENERATOR; same reason -- it names the roster it derives from",
}


def _exempt_reason(path_key: str) -> str:
    """The stated reason a path is not scanned, matched case-insensitively."""
    for name, reason in HANDLE_SCAN_EXEMPT_PATHS.items():
        if name.lower() == path_key:
            return reason
    return "unstated"

# Lowered companions of the path constants, DERIVED once so the scan compares like
# with like. Derived rather than hand-maintained — a second literal list would be
# the duplicated-knowledge defect one layer over.
_OUR_ADDED_PREFIXES_LOWER = tuple(x.lower() for x in OUR_ADDED_PREFIXES)
_HANDLE_SCAN_EXEMPT_PATHS_LOWER = {x.lower() for x in HANDLE_SCAN_EXEMPT_PATHS}


def _load_agent_handles(ref: str, root: Path) -> list[str]:
    """Load the fork-local fleet-handle denylist and verify its integrity stamp.

    Fail-closed: a missing file, malformed json, absent stamp, or a stamp that
    does not match the committed handles (a hand-edit that did not regenerate)
    raises GateError -> the gate exits 2 (could-not-run) rather than silently
    scanning with a tampered or empty denylist. This proves INTEGRITY only; a
    correctly-stamped but stale copy still passes -- freshness against the live
    roster is a fleet-level re-generation obligation, because a hash proves the
    bytes are unchanged, never that they are current.
    """
    # ATH-3397 (dexter, #59 re-read): the scan reads COMMITTED bytes at ``ref``, so
    # the denylist must come from that SAME ref. Reading it from the working tree
    # let the instrument's configuration and its subject come from different trees:
    # emptying the working-tree denylist made committed leaks stop being reported,
    # with nothing committed to show for it. Same class as reading a manifest from
    # the host while probing an image — config and subject must be one object.
    try:
        raw = _committed_bytes(ref, DENYLIST_REL, root)
    except Exception as exc:
        raise GateError(
            f"fleet-handle denylist unreadable at {ref}:{DENYLIST_REL} "
            f"(fail-closed): {exc}"
        )
    if not raw:
        raise GateError(
            f"fleet-handle denylist missing from the committed tree at "
            f"{ref}:{DENYLIST_REL} (fail-closed)"
        )
    try:
        payload = json.loads(raw.decode("utf-8"))
        raw_handles = payload["handles"]
        # dexter (#59, narrowed): the container must be a LIST. A JSON *string*
        # "abcdefgh" has len 8 and iterates into eight one-character "handles",
        # each of which is a non-empty string — so it cleared both the floor and
        # the entry check while compiling eight useless patterns.
        if not isinstance(raw_handles, list):
            raise GateError(
                "fleet-handle denylist 'handles' must be a LIST (fail-closed): got "
                f"{type(raw_handles).__name__}, which would iterate into characters"
            )
        handles = list(raw_handles)
        stamp = str(payload["stamp"])
        # a null/empty/non-string entry is a malformed denylist, not a handle: an
        # empty string would compile to a pattern that matches nothing useful while
        # still counting toward the floor.
        if not all(isinstance(h, str) and h.strip() for h in handles):
            raise GateError(
                "fleet-handle denylist contains a non-string or empty handle "
                "(fail-closed): every entry must be a non-empty string"
            )
        # dexter (#59/#76, third pass): the floor counted h.strip().casefold()
        # while the loader RETURNED — and the scanner COMPILED — the untrimmed h.
        # Eight distinct whitespace-wrapped names therefore cleared the floor while
        # the compiled patterns matched nothing: the floor measured a DIFFERENT
        # pattern set from the one that does the work. Entries must already be
        # canonical, so the set the floor counts is the set the scanner compiles.
        untrimmed = [h for h in handles if h != h.strip()]
        if untrimmed:
            raise GateError(
                "fleet-handle denylist entries carry surrounding whitespace "
                f"(fail-closed): {untrimmed[:3]!r} — entries must be canonical, or "
                "the floor counts a different pattern set than the scan compiles"
            )
    except (ValueError, KeyError, TypeError) as exc:
        raise GateError(f"fleet-handle denylist unreadable/malformed: {exc}")
    # ATH-3397 (dexter, #59 review): a CORRECTLY STAMPED but EMPTY list passes the
    # integrity check and compiles ZERO patterns — the gate then scans for nothing
    # and reports clean. The stamp proves the file was not hand-edited; it says
    # nothing about whether the file still has content. Truncation to empty (a bad
    # regeneration, a merge that dropped the array, a partial write) is exactly the
    # failure the stamp cannot see, so it is checked separately and fails CLOSED.
    #
    # MIN_HANDLES is a truncation tripwire, not a freshness check. It is set well
    # below the derived set (19 at the time of writing) so an ordinary roster change
    # never trips it, and high enough that a file gutted to one or two entries does.
    # Freshness against the live roster remains a fleet-level regeneration
    # obligation — a stamped but STALE list still passes here by construction.
    # Integrity: the stamp is verified against the DECLARED payload, exactly as
    # written in the file — never against the canonical form (see ORDER below).
    expected = hashlib.sha256("\n".join(sorted(handles)).encode()).hexdigest()
    if stamp != expected:
        raise GateError(
            "fleet-handle denylist stamp mismatch (hand-edited without "
            f"regenerating?): stamp={stamp[:12]} expected={expected[:12]}"
        )

    # STRUCTURAL (asabi ruling): canonicalise ONCE, after the stamp check, and let
    # the floor and the COMPILED PATTERNS consume the same list. Three fixes in a
    # row were each locally correct and each left a gap between what was VALIDATED
    # and what was USED — the shape invited it, because validation and enforcement
    # read the same variable through different transformations. One list closes
    # that shape rather than patching this instance.
    #
    # ORDER MATTERS: the stamp is verified against the DECLARED payload above,
    # never against the canonical form. Canonicalising first would let someone
    # alter whitespace without breaking the stamp — turning a fix for a bypass
    # into a new bypass.
    canonical = sorted({h.casefold() for h in handles})
    if len(canonical) < MIN_HANDLES:
        raise GateError(
            f"fleet-handle denylist yields {len(canonical)} unique handle(s) from "
            f"{len(handles)} entr(ies), below the truncation floor of {MIN_HANDLES} "
            "(fail-closed): a correctly stamped but emptied, gutted or duplicated "
            "denylist would leave this gate scanning for almost nothing"
        )
    return canonical


def _scan_committed(ref: str, root: Path) -> tuple[list[str], list[str], list[str]]:
    """Byte-scan every committed file. Returns (block, warn, skipped_binaries).

    Scans BYTES rather than ``git grep`` so files marked ``binary`` in
    ``.gitattributes`` -- notably the pinned tool logs, the likeliest place a
    real credential leaks -- are searched too; ``git grep -I`` would skip them.
    """
    always_res = [(label, re.compile(pat.encode())) for label, pat in BLOCK_ALWAYS]
    scoped_res = [(label, re.compile(pat.encode())) for label, pat in BLOCK_SCOPED]
    warn_res = [
        (label, re.compile(pat.encode()), (re.compile(ex.encode()) if ex else None))
        for label, pat, ex in WARN_PATTERNS
    ]
    # Fleet-agent handles (ATH-3397), loaded + stamp-verified from the generated
    # denylist. Word-boundary + case-insensitive so a handle like a short name
    # does not fire mid-word. Scoped to OUR_ADDED_PREFIXES (our authored
    # artifacts); upstream files that legitimately contain such a token are not
    # our leak. The denylist DATA file is excluded in the loop below.
    if HANDLE_FINDING_TIER not in ("warn", "block"):
        raise GateError(
            f"HANDLE_FINDING_TIER is {HANDLE_FINDING_TIER!r} (fail-closed): must be "
            "exactly 'warn' or 'block'."
        )
    agent_res = [
        # ATH-3439 pattern ruling: \b is the wrong boundary because `_` is a word
        # character, so \bquan\b misses quan_review / reviewer_quan — exactly how a
        # handle lands in a receipt FIELD NAME. `_` and `-` are not [a-z] so those
        # match; "quantum" and "banking" do not. Camel-embedded is a stated non-match.
        ("internal fleet-agent handle",
         re.compile(
             rb"(?i)(?<![a-z])("
             + b"|".join(re.escape(h).encode() for h in _load_agent_handles(ref, root))
             + rb")(?![a-z])"
         )),
    ]
    block: list[str] = []
    warn: list[str] = []
    skipped: list[str] = []
    for path in _committed_paths(ref, root):
        # STRUCTURAL: every DECISION consumes path_key, the normalised form; the
        # raw path survives only for committed-byte lookup and DISPLAY.
        path_key = path.lower()
        # No extension is derived any more: scope is decided by CONTENT (a NUL
        # byte) and by the named keep-set. Leaving `ext` computed-but-unused
        # would be the compute-then-ignore family this file has produced before.
        data = _committed_bytes(ref, path, root)
        if b"\x00" in data:
            skipped.append(f"{path} (binary: contains a NUL byte)")
            continue
        # Ambiguous host-path patterns fire only in files WE author; upstream's
        # own host paths (its .circleci etc.) are public-upstream content.
        in_our_scope = path_key.startswith(_OUR_ADDED_PREFIXES_LOWER)
        block_res = always_res + scoped_res if in_our_scope else always_res
        for lineno, line in enumerate(data.split(b"\n"), 1):
            shown = line.decode("utf-8", "replace").strip()[:200]
            for label, rx in block_res:
                if rx.search(line):
                    if _is_exempt(label, path, line):
                        continue
                    block.append(f"[{label}] {path}:{lineno}: {shown}")
            # Agent-handle scan: customer-artifact prose only (see the scope
            # constants above). Positive extension scope + enumerated exemptions.
            if in_our_scope and path_key in _HANDLE_SCAN_EXEMPT_PATHS_LOWER:
                note = f"{path} (exempt: {_exempt_reason(path_key)})"
                if note not in skipped:
                    skipped.append(note)
            elif in_our_scope:
                for label, rx in agent_res:
                    for _h in sorted({m.group(1).lower() for m in rx.finditer(line)}):
                        # TIER-ROUTED. This appended to `block` unconditionally,
                        # so HANDLE_FINDING_TIER was VALIDATED and then never
                        # used -- warn and block produced identical output and
                        # the staging tier did not stage. The guard above proved
                        # the constant was well-formed, which is not the same as
                        # proving it does anything.
                        sink = block if HANDLE_FINDING_TIER == "block" else warn
                        sink.append(f"[{label}] {path}:{lineno}: {shown}")
            for label, rx, ex in warn_res:
                if rx.search(line) and not (ex and ex.search(line)):
                    warn.append(f"[{label}] {path}:{lineno}: {shown}")
    return block, warn, skipped


def _run_receipt_verifier(root: Path) -> list[str]:
    """Run the package receipt verifier; fail-closed if absent/errored."""
    verifier = root / "athanor" / "verify_public_receipts.py"
    if not verifier.is_file():
        return [f"receipt verifier missing at {verifier.relative_to(root)} (fail-closed)"]
    proc = subprocess.run(
        [sys.executable, str(verifier)], cwd=root, capture_output=True, text=True
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()
        return [f"receipt verifier failed (rc={proc.returncode}): {detail}"]
    return []


def run_gate(ref: str = "HEAD", start: Path | None = None) -> tuple[list[str], list[str], list[str]]:
    """Return (block, warn, skipped_binaries). Raises GateError if it cannot run."""
    root = _repo_root(start or Path.cwd())
    block, warn, skipped = _scan_committed(ref, root)
    block.extend(_run_receipt_verifier(root))
    return block, warn, skipped


def scan_text(text: str, source: str = "pr-text") -> list[str]:
    """Run the ALWAYS-block patterns over arbitrary public text -- a PR body,
    review comment, or issue comment. These are public surfaces on a public fork
    that the committed-tree scan cannot see (they are GitHub metadata, not files),
    so an internal build-path or a token in a PR body is public + invisible to the
    file gate (the #14 body-leak class, ATH-2960).

    Reuses BLOCK_ALWAYS as the SINGLE source of truth so the text surface and the
    committed-tree surface can never drift. The BLOCK_SCOPED host-path patterns
    are intentionally NOT applied to prose (a bare home-directory path in a
    sentence is not an unambiguous leak), but our internal markers + secret tokens
    always are. (No verbatim forbidden literal appears in this docstring so the
    gate does not self-trip on its own source.)
    """
    res = [(label, re.compile(pat)) for label, pat in BLOCK_ALWAYS]
    findings: list[str] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for label, rx in res:
            if rx.search(line):
                findings.append(f"[{label}] {source}:{lineno}: {line.strip()[:200]}")
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ATH-2960 fork export-safety gate")
    parser.add_argument("--ref", default="HEAD", help="committed ref to scan (default HEAD)")
    parser.add_argument(
        "--warn-limit", type=int, default=40, help="max WARN lines to print (0 = all)"
    )
    parser.add_argument(
        "--scan-text",
        action="store_true",
        help="scan stdin (a PR/issue/review body) for BLOCK_ALWAYS internal markers "
        "+ secrets; exit 1 on a hit. Public-text surface companion to the file scan.",
    )
    args = parser.parse_args(argv)

    # PR bodies / review + issue comments are public surfaces on a public fork that
    # the committed-tree scan cannot see. Scan them with the SAME BLOCK_ALWAYS set.
    if args.scan_text:
        # Any failure to READ the text is a TOOL-ERROR (exit 2, legible
        # inconclusive), never a verdict (exit 1) or a clean pass (exit 0).
        # A closed/absent stdin makes sys.stdin None -> .read() raises
        # AttributeError (not OSError), and read-on-closed raises ValueError;
        # collapse all of these to the tool-error code so a broken input can
        # never masquerade as "leak found" or "clean".
        if sys.stdin is None:
            print("GATE-ERROR: no stdin available for --scan-text", file=sys.stderr)
            return 2
        try:
            text = sys.stdin.read()
        except (OSError, ValueError, AttributeError) as exc:
            print(f"GATE-ERROR: could not read text from stdin: {exc}", file=sys.stderr)
            return 2
        findings = scan_text(text)
        if findings:
            print(
                f"\nFAIL: {len(findings)} BLOCK-tier leak(s) in the PR/issue/review text:",
                file=sys.stderr,
            )
            for f in findings:
                print(f"  block: {f}", file=sys.stderr)
            print(
                "\nInternal markers/secrets are public on a public fork's PR page too "
                "-- scrub the PR body / comments.",
                file=sys.stderr,
            )
            return 1
        print("OK: PR/issue/review text clean (0 BLOCK-tier leaks).")
        return 0

    try:
        block, warn, skipped = run_gate(ref=args.ref)
    except GateError as exc:
        print(f"GATE-ERROR: {exc}", file=sys.stderr)
        return 2

    if skipped:
        print(f"INFO: {len(skipped)} genuine-binary file(s) not byte-scanned: {', '.join(skipped)}")

    if warn:
        print(f"WARN: {len(warn)} conscious-choice metadata finding(s) at {args.ref}:")
        shown = warn if args.warn_limit == 0 else warn[: args.warn_limit]
        for line in shown:
            print(f"  warn: {line}")
        if len(shown) < len(warn):
            print(f"  ... {len(warn) - len(shown)} more (raise --warn-limit to see all)")

        # UNCAPPED STAGED SECTION. WARN output is display-capped, and this fork has
        # thousands of conscious-choice warnings, so routing staged handle findings
        # into WARN alone buries them past the cap -- the staging tier would then
        # report a population nobody can see, which is the whole thing it exists to
        # do. Printed in full, separately, and only while staging.
        if HANDLE_FINDING_TIER == "warn":
            staged = [w for w in warn if w.startswith("[internal fleet-agent handle]")]
            if staged:
                print(
                    f"\nSTAGED (ATH-3397): {len(staged)} fleet-agent handle "
                    f"instance(s) at {args.ref} — REPORTED, not blocking. This tier "
                    "is promoted to BLOCK once the scrub lands:"
                )
                for line in staged:
                    print(f"  staged-handle: {line}")

    if block:
        print(
            f"\nFAIL: {len(block)} BLOCK-tier export-safety leak(s) at {args.ref}:",
            file=sys.stderr,
        )
        for line in block:
            print(f"  block: {line}", file=sys.stderr)
        print(
            "\nThese are hard-safety leaks on a PUBLIC fork. Remove them from the "
            "committed tree (do not commit generated *.replay.log; they belong in "
            "an ignored output dir).",
            file=sys.stderr,
        )
        return 1

    print(f"\nOK: export-safety gate clean at {args.ref} (0 BLOCK; {len(warn)} WARN).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
