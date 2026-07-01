# ibex_id_stage no_wb_prio_assign Candidate

This artifact records a selected-toolchain PPA and equivalence replay for the
`ibex_id_stage` default configuration.

## Transform

`no_wb_prio_assign` specializes the default `WritebackStage=0` exception
priority logic in `ibex_controller` from an `always_comb` priority chain to
explicit one-hot priority equations. The intended priority order is unchanged:

1. instruction fetch error
2. illegal instruction
3. ecall
4. ebreak
5. store error
6. load error

This remains a candidate package until the final toggle/power convention closes.

## Toolchain

- OSS CAD Suite 2026-06-30
- Yosys `0.66+181`
- Sky130 liberty:
  `sky130_fd_sc_hd__tt_025C_1v80.lib`
- OpenSTA `2.2.0`
- Timing convention: 10 ns clock on `clk_i`, 2 ns input/output delays,
  `rst_ni` false path.

## Selected-Toolchain PPA Filter

| Metric | Gold | Gate | Delta |
| --- | ---: | ---: | ---: |
| chip area | 7791.2224 | 7741.1744 | -0.6424% |
| top data arrival | 7.5917 ns | 5.54 ns | -27.03% |
| WNS/TNS | 0.00 / 0.00 | 0.00 / 0.00 | met / met |

Gold top path: `instr_rdata_i[31] -> csr_mtval_o[15]`.

Gate top path after the rewrite:
`instr_rdata_i[26] -> instr_valid_clear_o`.

## Local Formal Receipt

Local artifact-level equivalence was checked with Yosys `0.66+181` using
`equiv_make`, `async2sync`, `equiv_induct -undef -seq 32`, `equiv_simple`, and
`equiv_status`.

Result: `665` `$equiv` cells proven, `0` unproven.

An independent replay of the selected-toolchain area/timing result on the same
artifact hashes matched the positive direction:

- chip area: `7791.2224 -> 7741.1744`, `-0.6424%`
- top data arrival: `7.5917 ns -> 5.5358 ns`, `-27.08%`
- top-path slack: `0.4083 ns -> 2.4642 ns`

## Toggle Smoke

A quick Kairos random top-level toggle smoke over 200 cycles was run as an
early switching check:

| Metric | Gold | Gate | Delta |
| --- | ---: | ---: | ---: |
| internal VCD toggles | 26137 | 26468 | +1.27% |

This is not a realistic instruction-stream power replay, but it is enough to
avoid claiming toggle-flat solely from equivalence. Formal equivalence proves
matching observable behavior; it does not prove that implementation-internal
nodes switch identically under the current VCD counting convention.

Classification remains:
`formal_closed_area_positive_timing_positive_toggle_pending`.

## Formal Handoff Notes

Expected state relation for a sequential equivalence harness includes at least:

- Controller state:
  `controller_i.ctrl_fsm_cs`, `controller_i.nmi_mode_q`,
  `controller_i.debug_mode_q`, `controller_i.debug_cause_q`,
  `controller_i.load_err_q`, `controller_i.store_err_q`,
  `controller_i.exc_req_q`, `controller_i.illegal_insn_q`.
- ID-stage state:
  `id_fsm_q`, `branch_jump_set_done_q`, `imd_val_q`.
- Conditional generated state when parameters enable it:
  `g_branch_set_flop.branch_set_raw_q`,
  `g_sec_branch_taken.branch_taken_q`.

Use reset alignment before comparing architectural outputs. The candidate is not
customer/frontier material until the final toggle/power convention closes on
these exact hashes.

## Files

- `gold.v`: sv2v-converted V2001 gold design.
- `gate_no_wb_prio_assign.v`: sv2v-converted V2001 gate design.
- `gate_ibex_controller.sv`: source-level edited controller for review.
- `id_stage_10ns.sdc`: timing constraint used for OpenSTA replay.
- `gold_yosys66.log`, `gate_yosys66.log`: Yosys area replay logs.
- `gold_sta_yosys66.log`, `gate_sta_yosys66.log`: OpenSTA timing replay logs.
- `equiv_yosys66.ys`, `equiv_yosys66.log`: local equivalence replay script and log.
- `toggle_smoke_random_top_level.json`: quick random top-level toggle smoke.
- `SHA256SUMS`: artifact checksum manifest.
