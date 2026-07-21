# ibex_if_stage no_bp_prefetch_direct artifact package

This package contains the first local-positive `ibex_if_stage` candidate from the
selected Yosys 0.66 timing-aware scan.

Current classification:
`accepted_top_level_survivor_package_not_customer_frontier`

The original module-local package is preserved at the package root. The
`top_level_first/` subpackage records a current-master `ibex_top` replay against
commit `d36df4f695d7407dc67ac83728640b46bff4201e` using the top-level-first
gate. That replay is five-point positive:

- top-level selected-toolchain area improves `108441.5040 -> 108373.9392`
  (`-67.5648`, `-0.06231%`)
- all five recorded WNS groups improve
- artifact-level equivalence proves `1956/1956` `$equiv` cells
- pinned toggle convention is flat: `311729 -> 311729`

This is a survivor receipt, not a customer headline. PR #31 accepted the
top-level survivor package as engineering evidence on master. It is still not a
customer-facing frontier row: promotion requires the public frontier manifest
policy and the current proof-subject binding gate.

## Transform

Candidate: `no_bp_prefetch_direct`

The default public Ibex configuration has `BranchPredictor=0`. In that branch,
`predict_branch_taken` is statically zero and `branch_req` reduces to `pc_set_i`.
The gate specializes the prefetch branch/address mux for this no-BP branch:

```systemverilog
if (BranchPredictor) begin
  assign prefetch_branch = branch_req | nt_branch_mispredict_i;
  assign prefetch_addr   = branch_req ? {fetch_addr_n[31:1], 1'b0} : nt_branch_addr_i;
end else begin
  assign prefetch_branch = pc_set_i | nt_branch_mispredict_i;
  assign prefetch_addr   = pc_set_i ? {fetch_addr_n[31:1], 1'b0} : nt_branch_addr_i;
end
```

## Artifacts

- `gold.v`: sv2v-normalized combined Verilog-2001 for the default gold.
- `gate_no_bp_prefetch_direct.v`: sv2v-normalized combined Verilog-2001 for the gate.
- `gate_source.sv`: modified `ibex_if_stage.sv` source.
- `if_stage_10ns.sdc`: selected timing proxy used for local filter replay.
- `logs/`: selected Yosys 0.66 area logs and OpenSTA timing logs.
- `logs/convention_v1/`: pinned toggle-convention replay receipt, trace, VCD,
  and simulator log.
- `equiv_yosys66.ys`, `equiv_yosys66.log`: artifact-level Yosys equivalence
  replay script and log.
- `SHA256SUMS`: hashes for every replay artifact in this package.

Expected hashes:

```text
ebf8d55a86426034f93e7d7dc3ca793a41a5fcd221f125338e456383117a47a5  gold.v
3b110aa626ff94bd3491a092aede4b56eda5095c709b573a5c5b4a0efbc00427  gate_no_bp_prefetch_direct.v
0a8db48018564aaef876dc81bfb1703fc0049cf048c5b7120f83251aae6dca8c  gate_source.sv
```

## Local PPA Filter

Toolchain:

- Yosys `0.66+181`, OSS CAD Suite 2026-06-30
- OpenSTA `2.2.0`
- Sky130 HD liberty

Area:

- Gold chip area: `16821.132800`
- Gate chip area: `16756.070400`
- Delta: `-0.3868%`

Timing under `if_stage_10ns.sdc`:

- Gold top data arrival: `9.2829 ns`
- Gate top data arrival: `8.9149 ns`
- Delta: `-3.9654%`
- WNS/TNS: `0.00 / 0.00` for both gold and gate

## Formal Replay

Artifact-level equivalence was replayed with Yosys `0.66+181` using
`equiv_make`, `async2sync`, `equiv_induct -undef -seq 32`, `equiv_simple`, and
`equiv_status -assert`.

Result: `1956` `$equiv` cells proven, `0` unproven.

## Current Classification

`formal_closed_area_positive_timing_positive_toggle_flat_top_level_survivor`

The selected-toolchain area and timing replay is positive, and artifact-level
formal equivalence closes on these exact hashes. The corrected pinned toggle
convention is flat:

- Gold toggles: `311729`
- Gate toggles: `311729`
- Delta: `0.0%`
- Aliased VCD ids disambiguated: `17`

Final customer/frontier promotion still requires the public frontier manifest
policy and any additional review required for customer-facing use.

## #31 Provenance Note

PR #31 landed this package as an accepted top-level survivor artifact at merge
commit `ea0e5bc50e2322369a5cee166161acadbda417f0`. The package remains outside
`athanor/ppa_frontier/` because it is not a policy-pinned customer frontier row.

After #31, the formal workflow learned an explicit proof-subject binding guard:
the checked-out RTL under proof must match `SOURCE_DIFF.patch` applied to the
receipt's pinned `base_commit`. That guard is now enforced by
`athanor/verify_subject_binding.py` and its red-known #31-shaped regression
fixture, so future green formal rows cannot silently prove repository RTL while
the candidate only lives in the receipt patch.

## Current-Master Top-Level Replay

The current-master replay lives in `top_level_first/`.

Replay command:

```bash
python3 athanor/top_level_first.py \
  --patch <local-tmp>/ibex_if_stage_no_bp_prefetch_direct.patch \
  --core athanor/configs/ibex_top_yosys66.json \
  --candidate-name if_stage_no_bp_prefetch_direct_top_level \
  --unit ibex_if_stage \
  --out <local-tmp>/if_stage_no_bp_prefetch_direct_top_level \
  --force-fresh
```

The temporary patch was generated from the bounded source delta in this package:

```bash
diff -u --label a/rtl/ibex_if_stage.sv --label b/rtl/ibex_if_stage.sv \
  rtl/ibex_if_stage.sv \
  athanor_artifacts/if_stage_no_bp_prefetch_direct/gate_source.sv \
  > <local-tmp>/ibex_if_stage_no_bp_prefetch_direct.patch
```

Current replay result:

```text
FIVE-POINT POSITIVE
area: 108441.5040 -> 108373.9392 (-0.06231%)
overall WNS: -486.5999 ns -> -472.8057 ns (+13.7942 ns)
reg2reg WNS: -486.5999 ns -> -472.8057 ns (+13.7942 ns)
reg2out WNS: -437.8436 ns -> -424.0512 ns (+13.7924 ns)
in2reg WNS: -250.2307 ns -> -249.8900 ns (+0.3407 ns)
in2out WNS: -201.3074 ns -> -201.1313 ns (+0.1761 ns)
formal: 1956/1956 proven
toggle: 311729 -> 311729 (0.0%)
```

The older stacked scout that combined this no-BP transform with the accepted
expanded-predicate factoring regressed top-level area and timing, so that stack
is not used as evidence. The standalone no-BP transform is the survivor.

## Kairos Catch-Up Note

This candidate was driven by hand from the default public Ibex configuration:
`BranchPredictor=0` makes `predict_branch_taken` statically zero, so
`branch_req` reduces to `pc_set_i` in the selected branch. Kairos should learn a
parameter-specialized branch-mux rule that detects this reduction, emits the
bounded source rewrite, and routes it through top-level-first before spending
formal/toggle effort.

## Formal Handoff Notes

Top module: `ibex_if_stage`

Suggested first-pass state relation fields:

- IF stage state:
  - `instr_valid_id_q`
  - `instr_new_id_q`
  - IF/ID output registers: `instr_rdata_id_o`, `instr_rdata_alu_id_o`,
    `instr_rdata_c_id_o`, `instr_is_compressed_id_o`,
    `instr_gets_expanded_id_o`, `instr_expanded_id_o`, `instr_fetch_err_o`,
    `instr_fetch_err_plus2_o`, `illegal_c_insn_id_o`, `dummy_instr_id_o`,
    `pc_id_o`
- Prefetch buffer state:
  - `prefetch_buffer_i.valid_req_q`
  - `prefetch_buffer_i.discard_req_q`
  - `prefetch_buffer_i.rdata_outstanding_q`
  - `prefetch_buffer_i.branch_discard_q`
  - `prefetch_buffer_i.stored_addr_q`
  - `prefetch_buffer_i.fetch_addr_q`
- Fetch FIFO state under the prefetch buffer:
  - `prefetch_buffer_i.fifo_i.valid_q`
  - `prefetch_buffer_i.fifo_i.rdata_q`
  - `prefetch_buffer_i.fifo_i.err_q`
  - `prefetch_buffer_i.fifo_i.err_plus2_q`
  - `prefetch_buffer_i.fifo_i.instr_addr_q`
- Compressed decoder state:
  - `compressed_decoder_i.cm_rlist_q`
  - `compressed_decoder_i.cm_sp_offset_q`
  - `compressed_decoder_i.cm_state_q`

Inactive under default `BranchPredictor=0`:

- Branch predictor and skid-buffer state are generated but not active for this
  candidate's default-parameter replay.

Outputs to compare:

- Memory request/address and cache tieoffs:
  - `instr_req_o`, `instr_addr_o`, `ic_tag_*`, `ic_data_*`,
    `ic_scr_key_req_o`, `icache_ecc_error_o`
- IF/ID instruction outputs:
  - `instr_valid_id_o`, `instr_new_id_o`, `instr_rdata_id_o`,
    `instr_rdata_alu_id_o`, `instr_rdata_c_id_o`,
    `instr_is_compressed_id_o`, `instr_gets_expanded_id_o`,
    `instr_expanded_id_o`, `illegal_c_insn_id_o`
- Error/control/PC outputs:
  - `instr_intg_err_o`, `instr_fetch_err_o`, `instr_fetch_err_plus2_o`,
    `instr_bp_taken_o`, `dummy_instr_id_o`, `pc_if_o`, `pc_id_o`,
    `csr_mtvec_init_o`, `pc_mismatch_alert_o`, `if_busy_o`

Reset alignment is required. Use the same reset handling as the prior Ibex
ABC PDR closures.
