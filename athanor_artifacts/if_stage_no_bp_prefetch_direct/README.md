# ibex_if_stage no_bp_prefetch_direct artifact package

This package contains the first local-positive `ibex_if_stage` candidate from the
selected Yosys 0.66 timing-aware scan.

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

`formal_closed_area_positive_timing_positive_toggle_convention_pending`

The selected-toolchain area and timing replay is positive, and artifact-level
formal equivalence closes on these exact hashes. Final customer/frontier
promotion still requires the agreed toggle/power convention and packaged toggle
receipt.

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
