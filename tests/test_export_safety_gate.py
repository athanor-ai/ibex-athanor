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


def _padded(handles):
    """Fixture denylists must clear MIN_HANDLES (the truncation tripwire), so pad
    with filler names that appear in no fixture content."""
    filler = [f"fillerperson{i}" for i in range(esg.MIN_HANDLES)]
    return sorted(set(list(handles) + filler))


def _denylist_json(handles):
    """A denylist DATA file body with a correct integrity stamp for ``handles``."""
    import hashlib as _hl, json as _j
    hs = sorted(handles)
    return _j.dumps({"handles": hs, "stamp": _hl.sha256("\n".join(hs).encode()).hexdigest()})


def _git(args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _scan(tmp_path, files):
    """Commit ``files`` (rel -> content) into a temp repo and byte-scan HEAD.

    Returns (block, warn, skipped) from the SHIPPED ``_scan_committed`` -- the
    exact path CI runs, isolated from the receipt verifier.
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
    return esg._scan_committed("HEAD", tmp_path)



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


def test_agent_handle_in_customer_artifact_prose_is_block(tmp_path):
    # A handle in receipt/cert prose is a customer-facing IP leak -> BLOCK.
    # Capitalised to match how the real instances read (e.g. "(Quan/Ronald)").
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


def test_canonical_denylist_catches_the_bare_name_end_to_end(tmp_path):
    # the other direction: a canonical MIN-sized list loads AND the compiled
    # patterns actually catch the bare name in a customer artifact.
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
