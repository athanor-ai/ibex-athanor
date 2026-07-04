# ibex_if_stage expanded predicate factoring candidate

Classification:
`candidate_formal_ppa_positive_toggle_pending_cold_replay_pending`

This package records a top-level `ibex_top` replay for a general shared-term
factoring candidate in `ibex_if_stage`. It is not an accepted optimization yet:
toggle/activity evidence and independent cold replay are still pending.

## Transform

Candidate: `expanded_predicate_factor`

The source edit introduces one combinational predicate:

```systemverilog
assign instr_is_expanded = instr_gets_expanded == INSTR_EXPANDED;
```

and reuses that predicate where the IF-stage control path previously repeated
`!(instr_gets_expanded == INSTR_EXPANDED)`. The edit does not move state, add
state, change interfaces, or specialize an Ibex-only feature. It is a
shared-term factoring shape that should generalize to other RTL with repeated
control predicates.

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
| mapped cells | 13290 | 13334 | +44 / +0.3311% |
| overall WNS | -484.8247 ns | -470.9621 ns | +13.8626 ns |
| reg2reg WNS | -484.8247 ns | -470.9621 ns | +13.8626 ns |
| reg2out WNS | -436.0064 ns | -422.2023 ns | +13.8041 ns |
| in2reg WNS | -249.6181 ns | -249.4600 ns | +0.1581 ns |
| in2out WNS | -200.6972 ns | -200.5294 ns | +0.1678 ns |

Artifact-level formal equivalence:

- Engine: Yosys `equiv_make` + `async2sync` + `equiv_induct -undef -seq 32`
  + `equiv_simple` + `equiv_status -assert`
- Result: `1956/1956` `$equiv` cells proven, `0` unproven

## Current Boundary

This package is scout evidence for ATH-2699. It is deliberately not a README
headline row and not a customer win claim until the full bar closes:

1. source patch is bounded and replayable
2. formal equivalence is closed
3. top-level area and timing are positive
4. toggle/activity evidence is packaged
5. independent cold replay reproduces the package

Items 1-3 are included here. Items 4-5 are pending.

## Files

- `SOURCE_DIFF.patch`: source-level patch against `rtl/ibex_if_stage.sv`.
- `gate_source.sv`: gate source after applying the factoring edit.
- `gold.v`: sv2v-normalized combined Verilog-2001 gold artifact.
- `gate_expanded_predicate_factor.v`: sv2v-normalized combined Verilog-2001
  gate artifact.
- `equiv_yosys66.ys`, `equiv_yosys66.log`: formal replay script and log.
- `top_level_ppa_yosys66.json`: machine-readable top-level PPA/formal receipt.
- `reports/`: raw selected-toolchain top-level area and timing reports.
- `logs/`: raw synthesis and STA logs for baseline and gate top-level runs.
- `SHA256SUMS`: hashes for the full package.

## Module Naming

`SOURCE_DIFF.patch` applies directly to `rtl/ibex_if_stage.sv` and preserves the
module name `ibex_if_stage`. If a cold-replay workflow temporarily renames the
gate module with a `_gate` suffix for side-by-side checks, rename it back to
`ibex_if_stage` before running whole-core `ibex_top` synthesis.
