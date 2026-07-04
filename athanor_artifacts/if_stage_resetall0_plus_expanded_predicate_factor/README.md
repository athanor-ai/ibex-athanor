# ibex_if_stage ResetAll=0 plus expanded predicate candidate

Classification:
`candidate_five_point_positive_cold_replay_pending`

This package records a top-level `ibex_top` replay for an aggregate candidate in
`ibex_if_stage`:

1. the accepted expanded-predicate factoring from
   `if_stage_expanded_predicate_factor`, and
2. selected-toolchain `ResetAll=0` pruning of the IF/ID register reset branch.

The local top-level-first harness completed all five local legs. Independent
cold replay is still pending, so this package is not an accepted optimization
claim yet.

## Transform

Candidate: `resetall0_plus_expanded_predicate_factor`

The source edit introduces and reuses:

```systemverilog
assign instr_is_expanded = instr_gets_expanded == INSTR_EXPANDED;
```

It also specializes the `ResetAll=0` IF/ID register block used by the selected
top-level configuration, keeping the non-reset `always_ff @(posedge clk_i)`
implementation directly.

The edit does not add state, change interfaces, or change the selected
toolchain configuration. It is a selected-configuration constant-propagation
candidate stacked on the already accepted shared-term factoring candidate.

## Evidence Summary

Toolchain:

- OSS CAD Suite 2026-06-30
- Yosys `0.66+181`
- OpenSTA `2.2.0`
- sv2v `0.0.13`
- Sky130 liberty: `sky130_fd_sc_hd__tt_025C_1v80.lib`

Top-level selected-toolchain PPA:

| Metric | Baseline | Gate | Delta |
| --- | ---: | ---: | ---: |
| `ibex_top` chip area | 108428.9920 | 108397.7120 | -31.2800 / -0.02885% |
| overall WNS | -484.8247 ns | -470.9621 ns | +13.8626 ns |
| reg2reg WNS | -484.8247 ns | -470.9621 ns | +13.8626 ns |
| reg2out WNS | -436.0064 ns | -422.2023 ns | +13.8041 ns |
| in2reg WNS | -249.6181 ns | -249.4600 ns | +0.1581 ns |
| in2out WNS | -200.6972 ns | -200.5294 ns | +0.1678 ns |

Artifact-level formal equivalence:

- Engine: Yosys `equiv_make` + `async2sync` + `equiv_induct -undef -seq 32`
  + `equiv_simple` + `equiv_status -assert`
- Result: `1956/1956` `$equiv` cells proven, `0` unproven

Pinned toggle convention:

- Convention: `kairos.ibex.toggle.control_path.v1`
- Gold toggles: `311729`
- Gate toggles: `311729`
- Delta: `0.0%`
- Classification: `neutral_or_better`

## Current Boundary

This is a five-point local candidate package only. It remains
cold-replay-pending until a non-author independently reproduces the source
patch, top-level area/timing, formal replay, and toggle receipt.

Do not promote this package to an accepted win, aggregate whole-core percentage,
or customer-facing headline until the independent cold replay closes.

## Files

- `SOURCE_DIFF.patch`: aggregate source-level patch against
  `rtl/ibex_if_stage.sv`.
- `gold.v`, `gate.v`: sv2v-normalized combined Verilog-2001 artifacts.
- `equiv.ys`, `equiv.log`: formal replay script and log.
- `top_level_first_receipt.json`: machine-readable top-level-first receipt.
- `logs/convention_v1/`: pinned toggle-convention replay receipt, trace, VCD,
  and simulator work products.
- `reports/timing/`: raw selected-toolchain timing reports for baseline and
  gate.
- `logs/`: raw synthesis logs and area reports.
- `SHA256SUMS`: hashes for the full package.

## Module Naming

`SOURCE_DIFF.patch` applies directly to `rtl/ibex_if_stage.sv` and preserves the
module name `ibex_if_stage`. If a cold-replay workflow temporarily renames the
gate module with a `_gate` suffix for side-by-side checks, rename it back to
`ibex_if_stage` before running whole-core `ibex_top` synthesis.
