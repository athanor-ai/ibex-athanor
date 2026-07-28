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
import re
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


def _padded(handles):
    """Fixture denylists must clear MIN_HANDLES (the truncation tripwire), so pad
    with filler names that appear in no fixture content."""
    filler = [f"fillerperson{i}" for i in range(esg.MIN_HANDLES)]
    return sorted(set(list(handles) + filler))


def _denylist_json(handles):
    """A denylist DATA file body with a correct integrity stamp for ``handles``."""
    import hashlib as _hl
    import json as _j
    hs = sorted(handles)
    return _j.dumps({"handles": hs, "stamp": _hl.sha256("\n".join(hs).encode()).hexdigest()})


def _git(args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _first3(result):
    """The three columns most tests care about, from the wider shipped tuple."""
    return result[0], result[1], result[2]


def _scan_full(tmp_path, files):
    """All columns: (block, warn, binary_skipped, handle_exempt, handle_binary, handle_scope)."""
    _scan(tmp_path, files)
    return esg._scan_committed("HEAD", tmp_path)


def _scan(tmp_path, files):
    """Commit ``files`` (rel -> content) into a temp repo and byte-scan HEAD.

    Returns (block, warn, skipped) from the SHIPPED ``_scan_committed`` -- the
    exact path CI runs, isolated from the receipt verifier.

    ``_scan_committed`` also returns the handle-exemption list and the handle
    population; callers that care about those use ``_scan_full``.
    """
    files = dict(files)
    files.setdefault(esg.DENYLIST_REL, _denylist_json(_padded([_H_A, _H_B])))
    tmp_path.mkdir(parents=True, exist_ok=True)
    _git(["init", "-q"], tmp_path)
    _git(["config", "user.email", "t@example.invalid"], tmp_path)
    _git(["config", "user.name", "t"], tmp_path)
    for rel, content in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        _git(["add", rel], tmp_path)
    _git(["commit", "-q", "-m", "fixture"], tmp_path)
    return _first3(esg._scan_committed("HEAD", tmp_path))



def _repo_with_denylist(tmp_path, payload_text):
    """Commit ``payload_text`` as the denylist and return (ref, root)."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    _git(["init", "-q"], tmp_path)
    _git(["config", "user.email", "t@example.invalid"], tmp_path)
    _git(["config", "user.name", "t"], tmp_path)
    p = tmp_path / esg.DENYLIST_REL
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(payload_text)
    _git(["add", esg.DENYLIST_REL], tmp_path)
    _git(["commit", "-q", "-m", "denylist"], tmp_path)
    return "HEAD", tmp_path


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


def test_derive_handles_reads_humans_section_from_roster():
    # ATH-3427 (builder #943): humans (founders, teammates, external contacts)
    # live in roles.json's `humans` section now; the generator reads them there
    # instead of AST-parsing slack_post. A human handle must reach the denylist,
    # and a generic role-word must not.
    gen = _load_gen()
    name_a = "ai" + "dan"
    name_b = "an" + "ton"
    roles = {
        "roles": {"platform": {}, "maurice": {}},
        "humans": {name_a: {"slack_user_id": "U0"}, name_b: {"slack_user_id": "U1"},
                   "founder": {"slack_user_id": "U2"}},
        "_renames": {"perry": "platform"},
    }
    handles = gen.derive_handles(roles)
    assert name_a in handles and name_b in handles  # humans reach the denylist
    assert "maurice" in handles and "perry" in handles
    assert "founder" not in handles and "platform" not in handles  # generics filtered

def test_alt_handles_reach_the_derived_set():
    # asabi/Bob 2026-07-27: a denylist of canonical names does not catch a
    # founder alt-handle; KNOWN_ALT_HANDLES is the ATH-3427 stopgap and must
    # reach the derived set with no source-list entry.
    gen = _load_gen()
    handles = gen.derive_handles({"roles": {}, "_renames": {}})
    assert ("aidan" + "by") in handles
    assert ("hongsk" + "sam") in handles


def test_generation_reads_declared_builder_commit_not_worktree(tmp_path):
    # ATH-3427/#61: the generator reads roles.json (the single identity SSOT:
    # roles + humans + _renames) at the DECLARED commit via git show, never the
    # working tree — Dexter's hold, preserved through the single-source refactor.
    gen = _load_gen()
    builder = tmp_path / "builder"
    handoff = builder / "tools" / "agent-handoff"
    handoff.mkdir(parents=True)
    roles_path = handoff / "roles.json"
    roles_path.write_text(json.dumps(
        {"roles": {_H_A: {}, "research": {}}, "humans": {_H_B: {"slack_user_id": "U0"}},
         "_renames": {}}))
    _git(["init", "-q"], builder)
    _git(["config", "user.email", "t@example.invalid"], builder)
    _git(["config", "user.name", "t"], builder)
    _git(["add", "tools/agent-handoff/roles.json"], builder)
    _git(["commit", "-q", "-m", "authority"], builder)
    commit = subprocess.check_output(["git", "-C", str(builder), "rev-parse", "HEAD"], text=True).strip()

    # dirty the working tree AFTER the commit — must be ignored
    roles_path.write_text(json.dumps(
        {"roles": {"dirtyperson": {}, "research": {}}, "humans": {_H_C: {"slack_user_id": "U1"}},
         "_renames": {}}))

    out = tmp_path / "denylist.json"
    assert gen.main(["--source-repo", str(builder), "--source-ref", commit, "--out", str(out)]) == 0
    payload = json.loads(out.read_text())
    assert _H_A in payload["handles"] and _H_B in payload["handles"]  # committed content
    assert "dirtyperson" not in payload["handles"] and _H_C not in payload["handles"]  # worktree ignored
    assert payload["source"] == {
        "repo": "athanor-builder",
        "files": ["tools/agent-handoff/roles.json (roles + humans + _renames)"],
        "commit": commit,
        "ref": commit,
    }
    assert _H_A in payload["handles"] and _H_B in payload["handles"]
    assert "dirtyperson" not in payload["handles"] and _H_C not in payload["handles"]


# --- ATH-3397: fleet-agent handle GATE tests (derivation tests live above,
# landed via the infra split #61). ---


def test_agent_handle_in_customer_artifact_prose_is_block(tmp_path, monkeypatch):
    # A handle in receipt/cert prose is a customer-facing IP leak -> BLOCK.
    # Capitalised to match how the real instances read (e.g. "(Quan/Ronald)").
    #
    # The tier is PINNED here rather than inherited from the shipped default.
    # This test is about DETECTION; which sink a finding lands in is the staging
    # decision, and a detection test that silently depends on it breaks the
    # moment staging changes while telling you nothing about the detector.
    monkeypatch.setattr(esg, "HANDLE_FINDING_TIER", "block")
    leak = '{"note":"cross-VM replay required (' + _H_A.capitalize() + ')"}\n'
    block, _, _ = _scan(tmp_path, {"athanor_artifacts/pkt/formal_cert.json": leak})
    assert _has(block, "fleet-agent handle")
    assert _has(block, "formal_cert.json")


def test_generic_role_key_is_not_a_handle_hit(tmp_path):
    # False-positive control: role-keys ("builder"/"research") are ordinary
    # English and must NEVER flag, or the gate is disabled within a day.
    text = "the " + _RK + " pattern is common in this rtl\n"
    block, _, _ = _scan(tmp_path, {"athanor_artifacts/pkt/notes.md": text})
    assert not _has(block, "fleet-agent handle")


def test_denylist_data_file_is_exempt_not_self_flagged(tmp_path):
    # The denylist necessarily holds every handle verbatim; the enumerated
    # exemption must keep it from flagging itself.
    block, _, _ = _scan(tmp_path, {})  # only the injected denylist is committed
    assert not any("fleet-agent handle" in b and esg.DENYLIST_REL in b for b in block)


def test_tooling_py_source_is_out_of_handle_scope(tmp_path):
    # Positive .json/.md scope: an attribution comment in the fork's own .py
    # tooling is a contributor byline, not a customer surface -> not scanned.
    src = "# hardening pass reviewed by " + _H_A.capitalize() + "\n"
    block, _, _ = _scan(tmp_path, {"athanor/helper.py": src})
    assert not _has(block, "fleet-agent handle")


def test_denylist_stamp_mismatch_fails_closed(tmp_path):
    bad = json.dumps({"handles": _padded([_H_A, _H_B]), "stamp": "0" * 64})
    ref, root = _repo_with_denylist(tmp_path, bad)
    with pytest.raises(esg.GateError):
        esg._load_agent_handles(ref, root)


def test_missing_denylist_fails_closed(tmp_path):
    _git(["init", "-q"], tmp_path)
    _git(["config", "user.email", "t@example.invalid"], tmp_path)
    _git(["config", "user.name", "t"], tmp_path)
    (tmp_path / "x.txt").write_text("x")
    _git(["add", "x.txt"], tmp_path)
    _git(["commit", "-q", "-m", "no denylist"], tmp_path)
    with pytest.raises(esg.GateError):
        esg._load_agent_handles("HEAD", tmp_path)


def test_correctly_stamped_but_emptied_denylist_fails_closed(tmp_path):
    # dexter's #59 finding: the stamp proves the file was not hand-edited, NOT that
    # it still has content. Empty/gutted lists with VALID stamps compile zero
    # patterns and make the gate scan for nothing — they must fail closed.
    import hashlib as _hl
    for i, handles in enumerate(([], [_H_A], [_H_A, _H_B])):
        hs = sorted(handles)
        body = json.dumps({"handles": hs,
                           "stamp": _hl.sha256("\n".join(hs).encode()).hexdigest()})
        ref, root = _repo_with_denylist(tmp_path / f"r{i}", body)
        with pytest.raises(esg.GateError):
            esg._load_agent_handles(ref, root)


def test_a_full_denylist_still_loads(tmp_path):
    # control: the truncation floor must not reject a normal derived set.
    import hashlib as _hl
    handles = sorted(f"person{i}" for i in range(esg.MIN_HANDLES + 3))
    body = json.dumps({"handles": handles,
                       "stamp": _hl.sha256("\n".join(handles).encode()).hexdigest()})
    ref, root = _repo_with_denylist(tmp_path, body)
    assert esg._load_agent_handles(ref, root) == handles


def test_worktree_denylist_tamper_cannot_hide_committed_leaks(tmp_path):
    # dexter's #59 re-read: the scan reads COMMITTED bytes at --ref, so the denylist
    # must load from the SAME ref. Reading it from the working tree let anyone
    # silence the gate by emptying an UNCOMMITTED file — config and subject from
    # different trees.
    import hashlib as _hl
    good = _padded([_H_A, _H_B])
    body = json.dumps({"handles": good,
                       "stamp": _hl.sha256("\n".join(good).encode()).hexdigest()})
    ref, root = _repo_with_denylist(tmp_path, body)
    # now gut the WORKING TREE copy without committing it
    empty = json.dumps({"handles": [], "stamp": _hl.sha256(b"").hexdigest()})
    (root / esg.DENYLIST_REL).write_text(empty)
    assert esg._load_agent_handles(ref, root) == good  # committed content wins


def test_denylist_container_must_be_a_list_not_a_string(tmp_path):
    # dexter (#59): a JSON STRING "abcdefgh" has len 8 and iterates into eight
    # one-character handles, each a non-empty string — clearing a naive floor
    # while compiling nothing useful. Python duck typing hides it: every length
    # and iteration behaves plausibly while measuring CHARACTERS.
    import hashlib as _hl
    body = json.dumps({"handles": "abcdefgh",
                       "stamp": _hl.sha256("\n".join(sorted("abcdefgh")).encode()).hexdigest()})
    ref, root = _repo_with_denylist(tmp_path, body)
    with pytest.raises(esg.GateError):
        esg._load_agent_handles(ref, root)


def test_duplicate_handles_do_not_clear_the_floor(tmp_path):
    # dexter (#59): ["alpha"] * 8 is eight entries and ONE effective pattern.
    # The floor exists to prove distinct coverage, so it must count UNIQUE handles.
    import hashlib as _hl
    handles = ["alpha"] * esg.MIN_HANDLES
    body = json.dumps({"handles": handles,
                       "stamp": _hl.sha256("\n".join(sorted(handles)).encode()).hexdigest()})
    ref, root = _repo_with_denylist(tmp_path, body)
    with pytest.raises(esg.GateError):
        esg._load_agent_handles(ref, root)


def test_case_variants_are_not_distinct_handles(tmp_path):
    # the same name in different cases is one pattern (the scan is case-insensitive).
    import hashlib as _hl
    handles = sorted({f"Alpha{i % 2}" for i in range(2)} | {"ALPHA0", "alpha1"})
    body = json.dumps({"handles": handles,
                       "stamp": _hl.sha256("\n".join(handles).encode()).hexdigest()})
    ref, root = _repo_with_denylist(tmp_path, body)
    with pytest.raises(esg.GateError):
        esg._load_agent_handles(ref, root)


def test_floor_boundary_min_minus_one_fails_and_min_passes(tmp_path):
    # both sides of the boundary, so the floor cannot drift silently.
    import hashlib as _hl
    for n, should_pass in ((esg.MIN_HANDLES - 1, False), (esg.MIN_HANDLES, True)):
        handles = sorted(f"person{i}" for i in range(n))
        body = json.dumps({"handles": handles,
                           "stamp": _hl.sha256("\n".join(handles).encode()).hexdigest()})
        ref, root = _repo_with_denylist(tmp_path / f"n{n}", body)
        if should_pass:
            assert esg._load_agent_handles(ref, root) == handles
        else:
            with pytest.raises(esg.GateError):
                esg._load_agent_handles(ref, root)


def test_whitespace_wrapped_handles_fail_closed(tmp_path):
    # dexter (#59/#76, third pass): the floor counted h.strip().casefold() while the
    # loader returned — and the scanner compiled — the untrimmed h. Eight distinct
    # whitespace-wrapped names cleared the floor while matching nothing, because the
    # floor measured a DIFFERENT pattern set than the scan compiles.
    import hashlib as _hl
    wrapped = [f" name{i} " for i in range(esg.MIN_HANDLES)]
    body = json.dumps({"handles": wrapped,
                       "stamp": _hl.sha256("\n".join(sorted(wrapped)).encode()).hexdigest()})
    ref, root = _repo_with_denylist(tmp_path, body)
    with pytest.raises(esg.GateError):
        esg._load_agent_handles(ref, root)


def test_canonical_denylist_catches_the_bare_name_end_to_end(tmp_path, monkeypatch):
    # the other direction: a canonical MIN-sized list loads AND the compiled
    # patterns actually catch the bare name in a customer artifact.
    # Tier pinned: this is a DETECTION test, not a staging test.
    monkeypatch.setattr(esg, "HANDLE_FINDING_TIER", "block")
    import hashlib as _hl
    handles = sorted(f"name{i}" for i in range(esg.MIN_HANDLES))
    files = {
        esg.DENYLIST_REL: json.dumps(
            {"handles": handles,
             "stamp": _hl.sha256("\n".join(handles).encode()).hexdigest()}),
        "athanor_artifacts/pkt/receipt.json": '{"reviewer": "name3"}\n',
    }
    block, _, _ = _scan(tmp_path, files)
    assert _has(block, "fleet-agent handle")
    assert _has(block, "receipt.json")


def test_invalid_tier_fails_closed(tmp_path, monkeypatch):
    # dexter (#76): HANDLE_FINDING_TIER="blok" routed 32 live findings into the warn
    # bucket while the uncapped STAGED section (which runs only for exactly "warn")
    # stayed silent — exit 0, "gate clean", 32 instances invisible. A typo on the
    # one constant the promotion PR edits silently disabled the gate.
    monkeypatch.setattr(esg, "HANDLE_FINDING_TIER", "blok")
    with pytest.raises(esg.GateError):
        _scan(tmp_path, {"athanor_artifacts/pkt/receipt.json": '{"r": "' + _H_A + '"}\n'})


def test_both_valid_tiers_are_accepted(tmp_path, monkeypatch):
    # control: the guard must not reject the two legitimate values, or it would
    # simply break the gate rather than harden it.
    for tier in ("warn", "block"):
        monkeypatch.setattr(esg, "HANDLE_FINDING_TIER", tier)
        _scan(tmp_path / tier, {"athanor_artifacts/pkt/receipt.json": '{"r": "x"}\n'})


def test_the_tier_actually_ROUTES_the_finding(tmp_path, monkeypatch):
    """THE SELECTOR MUST SELECT.

    dexter: under BOTH warn and block a constructed handle produced BLOCK=1,
    WARN=0 -- the finding was appended to `block` unconditionally, so the tier
    constant was validated and then ignored. test_both_valid_tiers_are_accepted
    proved only that neither string raises, which is a different claim entirely:
    it cannot distinguish a working selector from one that is never read.
    """
    handle = _H_A
    tree = {"athanor_artifacts/pkt/receipt.json": '{"reviewer": "' + handle + '"}\n'}

    monkeypatch.setattr(esg, "HANDLE_FINDING_TIER", "block")
    block_b, warn_b, _ = _scan(tmp_path / "b", tree)
    monkeypatch.setattr(esg, "HANDLE_FINDING_TIER", "warn")
    block_w, warn_w, _ = _scan(tmp_path / "w", tree)

    handle_rows = lambda rows: [r for r in rows if "fleet-agent handle" in r]
    assert handle_rows(block_b) and not handle_rows(warn_b), (
        "block tier must route the finding to BLOCK", block_b, warn_b)
    assert handle_rows(warn_w) and not handle_rows(block_w), (
        "warn tier must route the finding to WARN and leave BLOCK empty -- "
        "otherwise staging does not stage", block_w, warn_w)


def test_artifact_extension_match_is_case_insensitive(tmp_path, monkeypatch):
    # dexter (#76): the scan normalised `ext` to lower case and then ignored it,
    # using path.endswith((".json",".md")) — so RECEIPT.JSON, a perfectly ordinary
    # way to name a published artifact, was never scanned at all.
    monkeypatch.setattr(esg, "HANDLE_FINDING_TIER", "block")
    for i, name in enumerate(("RECEIPT.JSON", "receipt.Json", "NOTES.MD", "notes.Md")):
        block, _, _ = _scan(tmp_path / f"e{i}",
                            {f"athanor_artifacts/pkt/{name}": '{"r": "' + _H_A + '"}\n'})
        assert _has(block, "fleet-agent handle"), f"{name} was not scanned"


def test_path_scope_decisions_are_case_insensitive(tmp_path, monkeypatch):
    # THE FIFTH INSTANCE of the compute-then-ignore family (asabi: at four, the file
    # needs a structural pass). Scope was decided on the RAW path, so
    # Athanor_Artifacts/pkt/receipt.json escaped OUR_ADDED_PREFIXES and was never
    # scanned at all. Every decision now consumes the normalised path_key; the raw
    # path survives only for DISPLAY.
    monkeypatch.setattr(esg, "HANDLE_FINDING_TIER", "block")
    for i, rel in enumerate((
        "athanor_artifacts/pkt/receipt.json",
        "Athanor_Artifacts/pkt/receipt.json",
        "ATHANOR_ARTIFACTS/pkt/RECEIPT.JSON",
    )):
        block, _, _ = _scan(tmp_path / f"p{i}", {rel: '{"r": "' + _H_A + '"}\n'})
        assert _has(block, "fleet-agent handle"), f"scope missed: {rel}"


def test_findings_display_the_original_path_casing(tmp_path, monkeypatch):
    # the raw path must still be what a reader sees, or the finding points at a file
    # that does not exist. Normalise for DECISIONS, display the original.
    monkeypatch.setattr(esg, "HANDLE_FINDING_TIER", "block")
    block, _, _ = _scan(tmp_path, {"Athanor_Artifacts/pkt/RECEIPT.JSON":
                                   '{"r": "' + _H_A + '"}\n'})
    assert any("Athanor_Artifacts/pkt/RECEIPT.JSON" in b for b in block), block


def test_handle_pattern_catches_identifier_forms(tmp_path, monkeypatch):
    # ATH-3439 pattern ruling applied here: `_` is a word character, so a \b-bounded
    # handle MISSES quan_review / reviewer_quan / created_by_quan — which is exactly
    # how a handle lands in a receipt field. These must all be caught.
    monkeypatch.setattr(esg, "HANDLE_FINDING_TIER", "block")
    for body in ('{"n": "' + _H_A + '_review"}',
                 '{"n": "reviewer_' + _H_A + '"}',
                 '{"d": "' + _H_A + '-ath2686-run"}',
                 '{"reviewer": "' + _H_A + '"}'):
        block, _, _ = _scan(tmp_path / f"r{abs(hash(body))%9999}",
                            {"athanor_artifacts/pkt/receipt.json": body + "\n"})
        assert _has(block, "fleet-agent handle"), f"identifier form missed: {body}"


def test_handle_pattern_does_not_flag_ordinary_vocabulary(tmp_path, monkeypatch):
    # THE NEGATIVE HALF (asabi: a suite that only proves necessity cannot detect
    # over-matching). A substring pattern would flag our own domain vocabulary —
    # "memory banking" is RTL optimisation language on a hardware product. These
    # must NOT be flagged, or the gate deletes the product's own words.
    monkeypatch.setattr(esg, "HANDLE_FINDING_TIER", "block")
    clean = [
        '{"note": "memory banking splits large memories"}',
        '{"note": "adversarial thinking is required"}',
        '{"note": "quantum quantity quantile"}',
        '{"note": "the platform and plate and plating"}',
    ]
    for i, body in enumerate(clean):
        block, _, _ = _scan(tmp_path / f"c{i}",
                            {"athanor_artifacts/pkt/notes.json": body + "\n"})
        assert not _has(block, "fleet-agent handle"), f"false positive on: {body}"


def test_the_shipped_tier_is_staging_until_the_scope_is_clean():
    """PIN THE SHIPPED CONFIGURATION.

    Every other tier test monkeypatches, so none of them notices which tier
    actually ships. The scope was just widened from an extension allow-list to a
    derived one and the live population went from 33 to thousands, so BLOCK here
    would enforce over a fork that has never been scrubbed at this scope --
    the configuration asabi called worse than no gate. Flip this to "block" only
    in the promotion PR, with the population at zero and a constructed bite.
    """
    assert esg.HANDLE_FINDING_TIER == "warn", (
        "the ibex handle gate is enforcing; it may only do so once the derived "
        "scope reports zero and the promotion carries a constructed-instance test"
    )


def test_the_handle_scan_has_no_extension_allow_list():
    """BEHAVIOUR, NOT SPELLING. Asserting a retired symbol's absence passes on a
    pure RENAME -- which is how BINARY_ASSET_EXT carried this class forward on
    the twin. Rejects ANY collection of dotted extension literals."""
    import ast
    import re as _re

    tree = ast.parse(Path(esg.__file__).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Set, ast.Tuple, ast.List)):
            continue
        lits = [e.value for e in node.elts if isinstance(e, ast.Constant)]
        dotted = [x for x in lits if isinstance(x, str) and _re.fullmatch(r"\.[a-z0-9]{1,6}", x)]
        assert len(dotted) < 3, (
            f"an extension allow-list is back in the gate ({dotted[:5]}); scope must "
            f"be derived -- every committed TEXT file, decided by content"
        )


# --- ported behavioural witnesses from the openc910 twin (#83 / 8edc85eb9) -----


def test_an_ascii_file_named_bin_is_scanned(tmp_path, monkeypatch):
    """The extension allow-list is gone; binary is decided by a NUL byte. An
    ASCII file named .bin is perfectly scannable and must be scanned. This is
    the BEHAVIOURAL witness -- the AST test alone can be satisfied by a single
    suffix condition rather than a collection."""
    monkeypatch.setattr(esg, "HANDLE_FINDING_TIER", "block")
    block, _, _ = _scan(tmp_path, {
        "athanor_artifacts/pkt/readable.bin": f"synthesis ran as {_H_A}\n"})
    assert _has(block, "readable.bin"), block


def test_a_handle_in_a_log_is_scanned(tmp_path, monkeypatch):
    """.log carried the live exposure on both forks and was outside the old scope."""
    monkeypatch.setattr(esg, "HANDLE_FINDING_TIER", "block")
    block, _, _ = _scan(tmp_path, {
        "athanor_artifacts/pkt/run.log": f"read_verilog .scratch/{_H_A}_scout/d.v\n"})
    assert _has(block, "run.log"), block


def test_a_real_binary_is_skipped_and_NAMED(tmp_path):
    """A genuine binary cannot be scanned -- that limitation is fine. It vanishing
    from the denominator in silence is not."""
    _scan(tmp_path, {"athanor_artifacts/pkt/real.bin": "PLACEHOLDER"})
    (tmp_path / "athanor_artifacts" / "pkt" / "real.bin").write_bytes(b"\x00\x01\x02")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True, check=False)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "bin"], cwd=tmp_path, capture_output=True, check=False)
    _b, _w, skipped, _exempt, _bin, _scope = esg._scan_committed("HEAD", tmp_path)
    assert any("real.bin" in s and "NUL byte" in s for s in skipped), skipped


def test_two_distinct_handles_on_one_line_give_two_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(esg, "HANDLE_FINDING_TIER", "block")
    block, _, _ = _scan(tmp_path, {
        "athanor_artifacts/pkt/pair.md": f"reviewed by {_H_A} and {_H_B}\n"})
    rows = [r for r in block if "pair.md" in r]
    assert len(rows) == 2, rows


def test_the_same_handle_twice_on_one_line_gives_one_row(tmp_path, monkeypatch):
    """Distinct-per-line, not per-occurrence: the twin measured 399 vs 444 and
    only one of those restores the original semantics."""
    monkeypatch.setattr(esg, "HANDLE_FINDING_TIER", "block")
    block, _, _ = _scan(tmp_path, {
        "athanor_artifacts/pkt/twice.md": f"{_H_A} and again {_H_A}\n"})
    rows = [r for r in block if "twice.md" in r]
    assert len(rows) == 1, rows


def test_the_handle_denominator_accounts_for_its_whole_population(tmp_path):
    """dexter: the INFO line claimed 'N genuine-binary files not byte-scanned'
    while counting handle EXEMPTIONS (which ARE byte-scanned for every other
    pattern) alongside upstream NUL files that were never in the handle
    population. Two categories in one list, and a denominator that was false in
    both directions."""
    _b, _w, skipped, exempt, _bin, scope = _scan_full(tmp_path, {
        "athanor_artifacts/pkt/a.md": "clean\n",
        "athanor_artifacts/pkt/b.json": "{}\n",
    })
    assert scope == (scope - len(exempt) - len(_bin)) + len(exempt) + len(_bin)
    assert scope >= 2, scope
    # the denylist is in scope and exempt; it must appear in exempt, not skipped
    assert any(esg.DENYLIST_REL in e for e in exempt), exempt
    assert not any(esg.DENYLIST_REL in s for s in skipped), skipped


def test_an_AUTHORED_binary_stays_in_the_handle_population(tmp_path):
    """dexter: the binary skip `continue`d BEFORE scope was computed, so an
    authored NUL file vanished from the handle denominator -- named in the global
    binary list and counted in no population at all. The equation balanced only
    because this corpus contains no in-scope binaries, which is correct by
    accident of the tree rather than by construction.

    A denominator test that plants only TEXT cannot see this class. This one
    plants an authored binary and an upstream one, and pins BOTH directions.
    """
    _scan(tmp_path, {"athanor_artifacts/pkt/authored.bin": "PLACEHOLDER",
                     "vendor/upstream/blob.bin": "PLACEHOLDER"})
    for rel in ("athanor_artifacts/pkt/authored.bin", "vendor/upstream/blob.bin"):
        (tmp_path / rel).write_bytes(b"\x00\x01binary\x00")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, capture_output=True, check=False)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "bins"], cwd=tmp_path, capture_output=True, check=False)
    _b, _w, skipped, exempt, handle_binary, scope = esg._scan_committed("HEAD", tmp_path)

    assert any("authored.bin" in x for x in handle_binary), (
        "an AUTHORED binary must stay in the handle population as unscannable",
        handle_binary)
    assert not any("blob.bin" in x for x in handle_binary), (
        "an UPSTREAM binary was never in the handle population", handle_binary)
    assert any("blob.bin" in x for x in skipped), ("upstream binary must still be "
                                                   "named globally", skipped)
    scanned = scope - len(exempt) - len(handle_binary)
    assert scanned + len(exempt) + len(handle_binary) == scope, (
        scanned, exempt, handle_binary, scope)


def _repo_with_a_live_handle_instance(tmp_path):
    """Commit a denylist plus a customer artifact containing one of its handles."""
    import hashlib as _hl
    handles = _padded([_H_A, _H_B])
    files = {
        esg.DENYLIST_REL: json.dumps(
            {"handles": handles,
             "stamp": _hl.sha256("\n".join(sorted(handles)).encode()).hexdigest()}),
        "athanor_artifacts/pkt/receipt.json": '{"reviewer": "' + _H_A + '"}\n',
    }
    tmp_path.mkdir(parents=True, exist_ok=True)
    _git(["init", "-q"], tmp_path)
    _git(["config", "user.email", "t@example.invalid"], tmp_path)
    _git(["config", "user.name", "t"], tmp_path)
    for rel, content in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        _git(["add", rel], tmp_path)
    _git(["commit", "-q", "-m", "live instance"], tmp_path)
    return tmp_path


_AFFIRMATIVE_CLEAN = "gate clean at"


def _repo_with_many_generic_warnings(tmp_path, count):
    """Commit ``count`` distinct GENERIC (non-handle) WARN findings.

    Generic on purpose: the staged handle section is uncapped, so only generic
    findings exercise --warn-limit, which is the path whose coverage claim is
    under test.
    """
    import hashlib as _hl
    handles = _padded([_H_A, _H_B])
    files = {
        esg.DENYLIST_REL: json.dumps(
            {"handles": handles,
             "stamp": _hl.sha256("\n".join(sorted(handles)).encode()).hexdigest()}),
    }
    for i in range(count):
        files[f"athanor/notes_{i}.md"] = f"see {POINTER} internal repo, note {i}\n"
    tmp_path.mkdir(parents=True, exist_ok=True)
    _git(["init", "-q"], tmp_path)
    _git(["config", "user.email", "t@example.invalid"], tmp_path)
    _git(["config", "user.name", "t"], tmp_path)
    for rel, content in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        _git(["add", rel], tmp_path)
    _git(["commit", "-q", "-m", "many warns"], tmp_path)
    return tmp_path


def _repo_with_no_findings(tmp_path):
    """Same shape as above but the artifact cites NO handle -- nothing to report.

    Deliberately identical in every other respect (same denylist, same paths, one
    committed artifact) so the only variable between this and the live-instance
    fixture is whether a finding exists.
    """
    import hashlib as _hl
    handles = _padded([_H_A, _H_B])
    files = {
        esg.DENYLIST_REL: json.dumps(
            {"handles": handles,
             "stamp": _hl.sha256("\n".join(sorted(handles)).encode()).hexdigest()}),
        "athanor_artifacts/pkt/receipt.json": '{"reviewer": "a-name-not-on-the-list"}\n',
    }
    tmp_path.mkdir(parents=True, exist_ok=True)
    _git(["init", "-q"], tmp_path)
    _git(["config", "user.email", "t@example.invalid"], tmp_path)
    _git(["config", "user.name", "t"], tmp_path)
    for rel, content in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        _git(["add", rel], tmp_path)
    _git(["commit", "-q", "-m", "no findings"], tmp_path)
    return tmp_path


def test_the_verdict_line_does_not_say_clean_while_reporting_findings(
    tmp_path, monkeypatch, capsys
):
    """CLEAN is a claim about the TREE. 0 BLOCK is a fact about the TIER.

    The summary line used to say ``gate clean`` whenever nothing reached BLOCK
    tier -- so on the real c910 main it printed CLEAN while naming 412 live
    fleet-agent-handle instances across 7 published artifacts on a PUBLIC fork.
    Accurate about what it measured, false about what it claimed, in the gate
    whose whole job is catching that, on the one line a reader quotes.

    Exit code is NOT the subject here: rc==0 is correct at WARN tier and the
    staging test above already pins it. This pins the WORD -- a verdict may use
    CLEAN only when there is nothing to report.
    """
    root = _repo_with_a_live_handle_instance(tmp_path)
    monkeypatch.setattr(esg, "HANDLE_FINDING_TIER", "warn")
    monkeypatch.setattr(esg, "_run_receipt_verifier", lambda root: [])
    monkeypatch.chdir(root)
    rc = esg.main(["--ref", "HEAD"])
    combined = "".join(capsys.readouterr())

    assert rc == 0, "tier behaviour must be unchanged: " + combined[-300:]
    verdict = [ln for ln in combined.splitlines() if ln.startswith("OK")]
    assert verdict, "no verdict line emitted: " + combined[-300:]
    line = verdict[-1]

    # The AFFIRMATIVE phrase, not the bare word. `"clean" in line` is true of
    # "NOT clean" -- substring-where-a-value-was-meant, which this repo has now
    # hit five times, once in the first draft of THIS test.
    assert _AFFIRMATIVE_CLEAN not in line, (
        "the verdict called the tree CLEAN while findings were reported above "
        "it. That is the defect this gate exists to catch, in its own summary: "
        + line
    )
    assert "NOT clean" in line, (
        "the verdict must SAY it is not clean, not merely omit the claim -- an "
        "omission reads as an oversight, a denial reads as a measurement: " + line
    )
    assert "WARN finding" in line, (
        "the verdict must carry the COUNT it is reporting, not just a denial: "
        + line
    )


def test_the_verdict_does_not_claim_coverage_the_display_cap_withheld(
    tmp_path, monkeypatch, capsys
):
    """THE SAME OVERCLAIM ONE FIELD OVER, in the fix for the overclaim.

    The first draft of the corrected verdict said "every finding is named
    above" -- false whenever --warn-limit bites, which is the DEFAULT. I had
    replaced a verdict that lied about CLEANLINESS with one that lied about
    COVERAGE, while writing the change whose entire subject is verdicts that
    claim more than they measured.

    So this pins the second claim the way the test above pins the first: when
    rows are withheld, the verdict must say how many, and it must not assert
    completeness.
    """
    root = _repo_with_many_generic_warnings(tmp_path, count=5)
    monkeypatch.setattr(esg, "_run_receipt_verifier", lambda root: [])
    monkeypatch.chdir(root)
    rc = esg.main(["--ref", "HEAD", "--warn-limit", "2"])
    combined = "".join(capsys.readouterr())

    assert rc == 0, combined[-300:]
    verdict = [ln for ln in combined.splitlines() if ln.startswith("OK")][-1]
    assert "not shown" in verdict, (
        "the cap withheld findings and the verdict did not say so: " + verdict
    )
    assert "all named above" not in verdict, (
        "the verdict claimed completeness the display did not deliver: " + verdict
    )

    # The withheld count must RECONCILE with the rows actually printed -- a
    # number that does not add up is the miscount this change exists to fix.
    shown = len([r for r in combined.splitlines() if r.strip().startswith("warn:")])
    withheld = int(re.search(r"(\d+) not shown", verdict).group(1))
    total = int(re.search(r"raised (\d+) WARN", verdict).group(1))
    assert shown + withheld == total, (
        f"shown {shown} + withheld {withheld} != reported total {total}; the "
        "row display and the verdict are counting different populations"
    )


def test_the_verdict_line_still_says_clean_when_there_is_nothing_to_report(
    tmp_path, monkeypatch, capsys
):
    """NARROWNESS CONTROL for the test above.

    A check that forbids the word CLEAN unconditionally would pass the previous
    test while destroying the verdict's only useful positive statement. So the
    clean tree must still be ABLE to say clean -- otherwise the fix is just a
    different false claim pointing the other way.
    """
    root = _repo_with_no_findings(tmp_path)
    monkeypatch.setattr(esg, "_run_receipt_verifier", lambda root: [])
    monkeypatch.chdir(root)
    rc = esg.main(["--ref", "HEAD"])
    combined = "".join(capsys.readouterr())

    assert rc == 0, combined[-300:]
    assert _AFFIRMATIVE_CLEAN in combined, (
        "a tree with nothing to report must still be reportable as clean: "
        + combined[-300:]
    )


def test_the_verdict_arithmetic_holds_on_a_MIXED_population(tmp_path, monkeypatch, capsys):
    """THE FIXTURE GAP THAT LET THE PORT SHIP WRONG. (dexter, ibex #63.)

    Every cap test here plants GENERIC warnings only. On a generic-only tree the
    naive `len(warn) - min(limit, len(warn))` and the correct
    `len(generic) - len(shown_generic)` are the SAME NUMBER -- so 67 tests passed
    while the live verdict said "4881 not shown" with 118 actually hidden.

    A cap test that cannot produce a mixed population cannot see a partition
    defect. This one plants BOTH kinds and asserts the identity:

        generic shown + staged shown + withheld == total

    That is the twin's 451-vs-367 miscount, and I reproduced it by porting the
    verdict WORDING without the partition underneath it.
    """
    import hashlib as _hl
    import re as _re

    handles = _padded([_H_A, _H_B])
    files = {
        esg.DENYLIST_REL: json.dumps(
            {"handles": handles,
             "stamp": _hl.sha256("\n".join(sorted(handles)).encode()).hexdigest()}),
    }
    # staged handle findings
    for i in range(4):
        files[f"athanor_artifacts/pkt/h{i}.md"] = f"reviewed by {_H_A}\n"
    # generic (non-handle) warnings
    for i in range(6):
        files[f"athanor/notes_{i}.md"] = f"see {POINTER} internal repo, note {i}\n"

    tmp_path.mkdir(parents=True, exist_ok=True)
    _git(["init", "-q"], tmp_path)
    _git(["config", "user.email", "t@example.invalid"], tmp_path)
    _git(["config", "user.name", "t"], tmp_path)
    for rel, content in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        _git(["add", rel], tmp_path)
    _git(["commit", "-q", "-m", "mixed"], tmp_path)

    monkeypatch.setattr(esg, "HANDLE_FINDING_TIER", "warn")
    # A synthetic tree has no receipt verifier, so the gate fail-closes on THAT
    # and never reaches the arithmetic under test -- a fixture artifact wearing
    # the shape of a real failure. Neutralised the same way the tier tests do.
    monkeypatch.setattr(esg, "_run_receipt_verifier", lambda root: [])
    monkeypatch.chdir(tmp_path)
    rc = esg.main(["--ref", "HEAD", "--warn-limit", "2"])
    out = "".join(capsys.readouterr())

    assert rc == 0, out[-300:]
    generic_rows = _re.findall(r"^  warn: (.*)$", out, _re.M)
    staged_rows = _re.findall(r"^  staged-handle: (.*)$", out, _re.M)
    verdict = [ln for ln in out.splitlines() if ln.startswith("OK")][-1]
    total = int(_re.search(r"raised (\d+) WARN", verdict).group(1))
    m = _re.search(r"(\d+) not shown", verdict)
    withheld = int(m.group(1)) if m else 0

    assert staged_rows, "the fixture produced no staged rows; it is generic-only again"
    assert generic_rows, "the fixture produced no generic rows"
    assert not (set(generic_rows) & set(staged_rows)), (
        "a finding was rendered in BOTH sections; it is then counted as hidden "
        "while visible: " + repr(sorted(set(generic_rows) & set(staged_rows))[:3])
    )
    assert len(generic_rows) + len(staged_rows) + withheld == total, (
        f"shown {len(generic_rows)}+{len(staged_rows)} + withheld {withheld} "
        f"!= total {total}; the verdict is counting a different population "
        f"than the display"
    )


def _mixed_repo(tmp_path, generic, staged):
    """A tree with exactly ``generic`` non-handle warnings and ``staged`` handle
    findings. Parameterised so the EMPTY-generic and EMPTY-staged shapes are
    constructible -- a fixture that always plants both cannot see a renderer
    nested under the wrong condition."""
    import hashlib as _hl
    handles = _padded([_H_A, _H_B])
    tmp_path.mkdir(parents=True, exist_ok=True)
    _git(["init", "-q"], tmp_path)
    _git(["config", "user.email", "t@example.invalid"], tmp_path)
    _git(["config", "user.name", "t"], tmp_path)
    files = {esg.DENYLIST_REL: json.dumps(
        {"handles": handles,
         "stamp": _hl.sha256("\n".join(sorted(handles)).encode()).hexdigest()})}
    for i in range(staged):
        files[f"athanor_artifacts/pkt/h{i}.md"] = f"reviewed by {_H_A}\n"
    for i in range(generic):
        files[f"athanor/n{i}.md"] = f"see {POINTER} internal repo, note {i}\n"
    for rel, content in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        _git(["add", rel], tmp_path)
    _git(["commit", "-q", "-m", "mixed"], tmp_path)
    return tmp_path


@pytest.mark.parametrize("generic, staged", [(0, 3), (3, 0), (3, 3)])
def test_every_population_shape_renders_what_the_verdict_counts(
    tmp_path, monkeypatch, capsys, generic, staged
):
    """THE STAGED RENDERER MUST NOT DEPEND ON THERE BEING GENERIC ROWS.

    (dexter, ibex #63 round 2.) It was nested under ``if generic:``, so a
    STAGED-ONLY tree rendered nothing at all while the verdict still reported
    "1 staged handle ... all named above". 68 tests passed through it because
    every cap fixture -- including the mixed-population one added for his
    PREVIOUS hold -- always plants generic rows.

    The assertion was never the problem. **A fixture that cannot produce the
    empty-generic case cannot see a renderer gated on generic being non-empty.**
    So this parameterises the shape and pins all three.
    """
    import re as _re

    root = _mixed_repo(tmp_path, generic, staged)
    monkeypatch.setattr(esg, "HANDLE_FINDING_TIER", "warn")
    monkeypatch.setattr(esg, "_run_receipt_verifier", lambda r: [])
    monkeypatch.chdir(root)
    rc = esg.main(["--ref", "HEAD"])
    out = "".join(capsys.readouterr())

    assert rc == 0, out[-300:]
    generic_rows = _re.findall(r"^  warn: ", out, _re.M)
    staged_rows = _re.findall(r"^  staged-handle: ", out, _re.M)
    verdict = [ln for ln in out.splitlines() if ln.startswith("OK")][-1]

    assert len(staged_rows) == staged, (
        f"verdict-vs-render mismatch: fixture planted {staged} staged finding(s) "
        f"and {len(staged_rows)} were rendered. Verdict line: {verdict}"
    )
    assert len(generic_rows) == generic, (
        f"fixture planted {generic} generic finding(s), {len(generic_rows)} rendered"
    )
    if staged:
        assert f"{staged} of them staged" in verdict, verdict
