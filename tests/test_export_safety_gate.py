"""Export-safety gate pattern coverage (ATH-2960 hardening).

Rail for the fail-open Quan found while reviewing openc910 #38: the internal
project namespace as a schema/module PATH (e.g. a receipt `schema` string or a
`from <ns>.sub import` line) matched NO pattern, and the ticket-id WARN was
case+hyphen pinned so `ath2852` (the natural machine form) evaded it.

Every internal-marker literal below is FRAGMENT-BUILT (never contiguous in this
source) so this committed test file does not self-trip the gate's own
committed-tree scan; the leak forms are reassembled at runtime and written into
throwaway temp git repos, which is where we WANT them.
"""
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

_GATE = Path(__file__).resolve().parent.parent / "athanor" / "export_safety_gate.py"
_spec = importlib.util.spec_from_file_location("export_safety_gate", _GATE)
esg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(esg)

# --- fragments: the contiguous marker bytes never appear in this file's source
NS = "kai" + "ros"            # internal project namespace
WD = "/work" + "dir"         # internal build path
POINTER = "athanor-" + NS    # internal repo pointer (WARN tier)
TICKET_DIGITS = "2852"
# AI-tool / vendor authorship markers -- fragment-built so the contiguous marker
# never appears in this committed test file (else it self-trips the gate's own
# committed-tree scan). Reassembled at runtime into throwaway fixtures.
TOOL = "Cla" + "ude"                       # AI-tool name
VENDOR = "anthro" + "pic"                  # AI-vendor name
FOOTER = "Generated with " + TOOL + " Code"  # the bot auto-attribution footer


def _git(args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _scan(tmp_path, files):
    """Commit ``files`` (rel -> content) into a temp repo and byte-scan HEAD.

    Returns (block, warn, skipped) from the SHIPPED ``_scan_committed`` -- the
    exact path CI runs, isolated from the receipt verifier.
    """
    _git(["init", "-q"], tmp_path)
    _git(["config", "user.email", "t@example.invalid"], tmp_path)
    _git(["config", "user.name", "t"], tmp_path)
    for rel, content in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        _git(["add", rel], tmp_path)
    _git(["commit", "-q", "-m", "fixture"], tmp_path)
    return esg._scan_committed("HEAD", tmp_path)


def _has(entries, needle):
    return any(needle in e for e in entries)


# --- the fix: namespace schema/module path is BLOCK ------------------------

def test_kairos_namespace_schema_path_is_block(tmp_path):
    # the REAL #38 leak form: a receipt schema string
    leak = '  "schema": "' + NS + "." + "ath" + TICKET_DIGITS + '.helper_parent_area_scout.v1"\n'
    block, warn, _ = _scan(tmp_path, {"athanor/receipt.json": leak})
    assert _has(block, "Kairos namespace"), block


def test_kairos_module_import_path_is_block(tmp_path):
    leak = "from " + NS + ".sv_bundle_parse import convert\n"
    block, warn, _ = _scan(tmp_path, {"athanor/helper.py": leak})
    assert _has(block, "Kairos namespace"), block


# --- the fix: AI-tool / vendor authorship footer is BLOCK (asabi ruling) ---

def test_ai_tool_footer_committed_is_block(tmp_path):
    # the real recurring leak: the bot attribution footer in a committed file
    block, warn, _ = _scan(tmp_path, {"athanor/notes.md": "// " + FOOTER + "\n"})
    assert _has(block, "AI-tool authorship footer"), block
    assert _has(block, "AI-tool name"), block  # broad token net also fires


def test_ai_vendor_coauthor_trailer_committed_is_block(tmp_path):
    # the co-author trailer form: "<tool> <noreply@<vendor>.com>"
    leak = "Co-Authored-By: " + TOOL + " <noreply@" + VENDOR + ".com>\n"
    block, warn, _ = _scan(tmp_path, {"athanor/notes.md": leak})
    assert _has(block, "AI-vendor name"), block


def test_ai_tool_footer_in_pr_body_text_is_block():
    # Quan's ask: a FRESH fork PR body carrying the footer must red via the
    # PR-text surface (scan_text) -- the committed-tree scan cannot see PR
    # metadata, and the footer is exactly what lands there. Same BLOCK_ALWAYS
    # source of truth, so committed-tree and PR-text can never drift.
    body = "This PR ports the branch-predictor encoder table.\n\n" + FOOTER + "\n"
    findings = esg.scan_text(body, source="pr-body")
    assert _has(findings, "AI-tool authorship footer"), findings


def test_ai_tool_name_is_case_insensitive(tmp_path):
    # footer casing varies across bots; the (?i) net must catch a lowercased form
    block, warn, _ = _scan(tmp_path, {"athanor/x.md": "built by " + TOOL.lower() + "\n"})
    assert _has(block, "AI-tool name"), block


def test_ordinary_words_are_not_a_false_ai_tool_hit(tmp_path):
    # precision: 'cla'+'ude' is a specific token -- words that merely share a
    # prefix ('clause', 'cladding') or contain 'clude' ('included') are NOT the
    # tool name and must never false-block a legitimate RTL/prose line.
    clean = "the included clause of the cladding module is public\n"
    block, warn, _ = _scan(tmp_path, {"athanor/rtl.v": clean})
    assert not _has(block, "AI-tool name"), block
    assert not _has(block, "AI-vendor name"), block


def test_allowed_verdict_tools_are_not_blocked(tmp_path):
    # The owner boundary (Quan control): the VERDICT tools -- Yosys / OpenSTA /
    # Lean -- are public BY DESIGN (our posture names them). Only the proprietary
    # proposal-side AI-tool/vendor markers are the leak. Naming a verdict tool in
    # a committed receipt/README must NEVER trip the vendor class.
    ok = "Verified with Yosys + OpenSTA; the proof was discharged in Lean.\n"
    block, warn, _ = _scan(tmp_path, {"athanor/receipt_notes.md": ok})
    assert not _has(block, "AI-tool name"), block
    assert not _has(block, "AI-vendor name"), block
    assert not _has(block, "AI-tool authorship footer"), block


# --- tier preservation: the repo pointer stays WARN, never upgraded --------

def test_repo_pointer_plain_stays_warn_not_block(tmp_path):
    block, warn, _ = _scan(tmp_path, {"athanor/notes.md": "see " + POINTER + " internal repo\n"})
    assert not _has(block, "Kairos namespace"), block
    assert _has(warn, "Kairos-repo pointer"), warn


def test_repo_pointer_dotted_form_is_not_upgraded_to_block(tmp_path):
    # (?<!athanor-) must keep the dotted repo URL out of the namespace BLOCK
    block, warn, _ = _scan(tmp_path, {"athanor/notes.md": "clone " + POINTER + ".git\n"})
    assert not _has(block, "Kairos namespace"), block
    assert _has(warn, "Kairos-repo pointer"), warn


# --- the fix: ticket id is case-insensitive + hyphen-optional (WARN) -------

@pytest.mark.parametrize("ticket", [
    "A" + "TH-" + TICKET_DIGITS,    # ATH-2852  (original form, still WARN)
    "a" + "th-" + TICKET_DIGITS,    # ath-2852  (lowercase)
    "a" + "th" + TICKET_DIGITS,     # ath2852   (lowercase, no hyphen -- the evader)
    "A" + "th-" + TICKET_DIGITS,    # Ath-2852  (mixed case)
    "A" + "TH" + TICKET_DIGITS,     # ATH2852   (upper, no hyphen)
])
def test_ticket_id_case_and_hyphen_variants_warn(tmp_path, ticket):
    block, warn, _ = _scan(tmp_path, {"athanor/r.json": '  "ref": "' + ticket + '"\n'})
    assert _has(warn, "Linear ticket id"), (ticket, warn)


def test_datapath_digits_are_not_a_false_ticket(tmp_path):
    # leading \b keeps the widened ticket pattern off in-word digits
    block, warn, _ = _scan(tmp_path, {"athanor/rtl.v": "wire " + "datapath" + "2960" + ";\n"})
    assert not _has(warn, "Linear ticket id"), warn


# --- positive controls: unrelated tiers unchanged --------------------------

def test_workdir_path_still_blocks(tmp_path):
    block, warn, _ = _scan(tmp_path, {"athanor/log.txt": "at " + WD + "/athanor/x\n"})
    assert _has(block, "workdir"), block


def test_clean_tree_is_silent(tmp_path):
    block, warn, _ = _scan(tmp_path, {"athanor/ok.txt": "a plain public line\n"})
    assert block == [] and warn == [], (block, warn)


# --- scanner is the sole discriminator (seeded secret + valid manifest) ----

def test_scanner_blocks_namespace_independent_of_valid_receipt_manifest(tmp_path):
    # Seed the namespace into a committed artifact AND give it a VALID SHA256SUMS
    # entry. The byte-scanner must block regardless of the manifest verifying --
    # the scanner, not the receipt hash, is the sole discriminator.
    leak = NS + "." + "ath" + TICKET_DIGITS + ".scout.v1\n"
    digest = hashlib.sha256(leak.encode()).hexdigest()
    sums = digest + "  receipt.json\n"
    block, warn, _ = _scan(tmp_path, {
        "athanor_artifacts/receipt.json": leak,
        "athanor_artifacts/SHA256SUMS": sums,
    })
    assert _has(block, "Kairos namespace"), block


# --- span-bound exemptions (Dexter verdict, ibex #53) -----------------------

_ABLATION_DIR = "athanor_artifacts/ibex_fetch_fifo_native_agent_ablation/"
_CONV_ID = "kai" + "ros.ibex.toggle.control_path.v1"


def test_ai_tool_inside_ablation_subtree_is_exempt(tmp_path):
    content = "launched via " + TOOL + " Code one-shot\n"
    block, warn, _ = _scan(tmp_path, {_ABLATION_DIR + "README.md": content})
    assert not _has(block, "AI-tool name"), block


def test_ai_vendor_inside_ablation_subtree_is_exempt(tmp_path):
    content = "OAuth-served " + VENDOR + " subscription\n"
    block, warn, _ = _scan(tmp_path, {_ABLATION_DIR + "notes.md": content})
    assert not _has(block, "AI-vendor name"), block


def test_ai_footer_outside_ablation_still_blocks(tmp_path):
    content = "// " + FOOTER + "\n"
    block, warn, _ = _scan(tmp_path, {"athanor/other.md": content})
    assert _has(block, "AI-tool authorship footer"), block


def test_fleet_identifier_inside_ablation_still_blocks(tmp_path):
    content = "see " + WD + "/fleet for details\n"
    block, warn, _ = _scan(tmp_path, {_ABLATION_DIR + "readme.md": content})
    assert _has(block, "workdir"), block


def test_secret_token_inside_ablation_still_blocks(tmp_path):
    content = "key: ghp_" + "A" * 30 + "\n"
    block, warn, _ = _scan(tmp_path, {_ABLATION_DIR + "config.json": content})
    assert _has(block, "GitHub token"), block


def test_convention_id_at_exact_path_is_exempt(tmp_path):
    content = '"convention_id": "' + _CONV_ID + '"\n'
    block, warn, _ = _scan(tmp_path, {
        "athanor_artifacts/if_stage_expanded_predicate_factor/receipt.json": content,
    })
    assert not _has(block, "Kairos namespace"), block


def test_convention_id_at_toolchain_policy_is_exempt(tmp_path):
    content = '"id": "' + _CONV_ID + '"\n'
    block, warn, _ = _scan(tmp_path, {"athanor/toolchain_policy.json": content})
    assert not _has(block, "Kairos namespace"), block


def test_different_kairos_namespace_at_convention_path_still_blocks(tmp_path):
    different_ns = "kai" + "ros.ibex.OTHER_protocol.v2"
    content = '"convention_id": "' + different_ns + '"\n'
    block, warn, _ = _scan(tmp_path, {
        "athanor_artifacts/if_stage_expanded_predicate_factor/receipt.json": content,
    })
    assert _has(block, "Kairos namespace"), block


def test_convention_id_at_non_exempt_path_still_blocks(tmp_path):
    content = '"convention_id": "' + _CONV_ID + '"\n'
    block, warn, _ = _scan(tmp_path, {"athanor/other_file.json": content})
    assert _has(block, "Kairos namespace"), block


# --- ATH-3397 denylist-infra: roster-derivation tests (generator only; the
# gate that CONSUMES the denylist rides the separate red-by-design PR #59).
# Handles fragment-built per this file's convention.
import importlib.util as _ilu

_H_A = "qu" + "an"
_H_B = "ai" + "dan"
_H_C = "an" + "ton"
_RK = "buil" + "der"


def _load_gen():
    gen_path = Path(__file__).resolve().parent.parent / "athanor" / "gen_fleet_handle_denylist.py"
    spec = _ilu.spec_from_file_location("gen_fhd_infra", gen_path)
    gen = _ilu.module_from_spec(spec)
    spec.loader.exec_module(gen)
    return gen


def test_derive_handles_excludes_role_keys_includes_persons():
    gen = _load_gen()
    roles = {"roles": {"platform": {}, "maurice": {}, "research": {}},
             "_renames": {"perry": "platform", _H_A: "qa", _RK: _RK}}
    handles = gen.derive_handles(roles)
    assert "perry" in handles and "maurice" in handles and _H_A in handles
    assert "platform" not in handles and "research" not in handles and _RK not in handles


def test_non_agent_names_unioned_and_generic_founder_excluded():
    gen = _load_gen()
    src = ('_NON_AGENT_ROLES = {\n    "founder": "U0",\n'
           f'    "{_H_B}": "U0",\n    "{_H_C}": "U1",\n}}\n')
    extra = gen.extract_non_agent_names(src)
    assert _H_B in extra and _H_C in extra and "founder" in extra  # raw keys
    handles = gen.derive_handles({"roles": {"maurice": {}}, "_renames": {}}, extra)
    assert _H_B in handles and _H_C in handles and "maurice" in handles
    assert "founder" not in handles  # generic role-word filtered at derivation


def test_extract_non_agent_names_fails_loud_when_absent():
    gen = _load_gen()
    with pytest.raises(ValueError):
        gen.extract_non_agent_names("OTHER = {}\n")


def test_alt_handles_reach_the_derived_set():
    # asabi/Bob 2026-07-27: a denylist of canonical names does not catch a
    # founder alt-handle; KNOWN_ALT_HANDLES is the ATH-3427 stopgap and must
    # reach the derived set with no source-list entry.
    gen = _load_gen()
    handles = gen.derive_handles({"roles": {}, "_renames": {}})
    assert ("aidan" + "by") in handles
    assert ("hongsk" + "sam") in handles


def test_generation_reads_declared_builder_commit_not_worktree(tmp_path):
    gen = _load_gen()
    builder = tmp_path / "builder"
    handoff = builder / "tools" / "agent-handoff"
    handoff.mkdir(parents=True)
    roles_path = handoff / "roles.json"
    slack_post_path = handoff / "slack_post"
    roles_path.write_text(json.dumps({"roles": {_H_A: {}, "research": {}}, "_renames": {}}))
    slack_post_path.write_text(f'_NON_AGENT_ROLES = {{"{_H_B}": "U0"}}\n')
    _git(["init", "-q"], builder)
    _git(["config", "user.email", "t@example.invalid"], builder)
    _git(["config", "user.name", "t"], builder)
    _git(["add", "tools/agent-handoff/roles.json", "tools/agent-handoff/slack_post"], builder)
    _git(["commit", "-q", "-m", "authority"], builder)
    commit = subprocess.check_output(["git", "-C", str(builder), "rev-parse", "HEAD"], text=True).strip()

    roles_path.write_text(json.dumps({"roles": {"dirtyperson": {}, "research": {}}, "_renames": {}}))
    slack_post_path.write_text(f'_NON_AGENT_ROLES = {{"{_H_C}": "U1"}}\n')

    out = tmp_path / "denylist.json"
    assert gen.main(["--source-repo", str(builder), "--source-ref", commit, "--out", str(out)]) == 0
    payload = json.loads(out.read_text())
    assert payload["source"] == {
        "repo": "athanor-builder",
        "files": [
            "tools/agent-handoff/roles.json",
            "tools/agent-handoff/slack_post (_NON_AGENT_ROLES)",
        ],
        "commit": commit,
        "ref": commit,
    }
    assert _H_A in payload["handles"] and _H_B in payload["handles"]
    assert "dirtyperson" not in payload["handles"] and _H_C not in payload["handles"]
