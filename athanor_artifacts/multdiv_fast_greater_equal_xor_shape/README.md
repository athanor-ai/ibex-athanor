# ibex_multdiv_fast greater_equal_xor_shape

Status: accepted artifact.

This package records the `ibex_multdiv_fast` compare-mux rewrite on
`is_greater_equal`. The change is the same XOR/AND/OR producer-shape family as
the accepted `ibex_multdiv_slow` win, applied to the fast multiplier/divider.

## Customer Result

| Vector | Gold | Gate | Delta |
| --- | ---: | ---: | ---: |
| Mapped cells | 3306 | 3306 | 0 saved / 0.00% |
| Timing max propagation delay | 10.85ns | 10.57ns | -0.28ns / -2.58% |
| Toggle/activity | 7657 | 7657 | 0.00% |
| Formal equivalence | 772 proven, 0 unproven | 772 proven, 0 unproven | proved |

Independent cold replay also reproduced the same source diff, area improvement
under the replayed selected flow, timing improvement, and formal equivalence.
The packaged toggle result is corroborated by exact VCD equality.

## Measurement Convention

- Toolchain: OSS CAD Suite 2026-06-30, Yosys 0.66+181, OpenSTA.
- Timing convention: `combinational_max_propagation_delay`.
- Area/cell convention: one-button raw-SystemVerilog source-prep cell metric.
- Toggle convention: deterministic VCD replay under the packaged stimulus.

## Files

- `SOURCE_DIFF.patch`: module rename plus the one functional expression rewrite.
- `gold_source.sv`: original source used for the package.
- `gate_greater_equal_xor_shape.v`: rewritten gate source.
- `public_receipt.json`: customer-safe result summary.
- `artifacts/*.vcd` and `artifacts/*.saif`: packaged toggle/activity traces.
