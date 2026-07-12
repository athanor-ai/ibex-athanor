# ibex_multdiv_slow greater_equal_xor_shape Candidate

This package records a replayed `ibex_multdiv_slow` selected-toolchain
optimization artifact.

Classification:
`area_positive_timing_positive_yosys_equivalence_closed_toggle_flat`

This package is accepted module-level artifact evidence for the stated
toolchain. Promotion into the customer-facing `athanor/ppa_frontier/` layout
and main optimized RTL is a separate integration step.

## Transform

Candidate: `greater_equal_xor_shape`

The source-level edit is a one-expression rewrite of the signed compare helper
used by the division path:

```systemverilog
assign is_greater_equal = ((accum_window_q[31] ^ op_b_shift_q[31]) & accum_window_q[31]) |
    (~(accum_window_q[31] ^ op_b_shift_q[31]) & ~res_adder_h[31]);
```

The package includes `SOURCE_DIFF.patch` so reviewers can confirm that the
source edit is limited to this replacement.

## Files

- `gold_source.sv`: original `ibex_multdiv_slow.sv` source.
- `gate_source.sv`: source with the `greater_equal_xor_shape` edit.
- `SOURCE_DIFF.patch`: source-level one-expression diff.
- `gold.v`: Verilog-2001 gold artifact used for replay.
- `gate_greater_equal_xor_shape.v`: Verilog-2001 gate artifact used for replay.
- `replay_area.py`: selected Yosys area replay.
- `replay_timing.py`: OpenSTA timing replay using the selected 10 ns / 2 ns I/O
  proxy convention.
- `replay_equiv_yosys66.ys`, `replay_equiv.sh`: Yosys sequential equivalence
  replay.
- `toggle_proxy.json`: deterministic 200-cycle toggle proxy receipt.
- `ath2924_public_replay_receipt.json`: public machine-readable receipt from
  the ATH-2924 OpenSTA timing-route conversion replay.
- `ath2924_timing_conversion_receipt.json`: source local replay receipt kept
  for traceability; the public receipt above removes local-only context.
- `INPUT_SHA256SUMS`: hashes for the primary replay inputs.
- `SHA256SUMS`: hashes for the full package.

## Toolchain

- Yosys `0.66+181`, OSS CAD Suite 2026-06-30
- OpenSTA `2.2.0`
- Sky130 HD liberty: `sky130_fd_sc_hd__tt_025C_1v80.lib`
- Timing convention: 10 ns clock on `clk_i`, 2 ns input/output delays, and
  `rst_ni` false path.

The replay scripts intentionally take tool paths from environment variables:

```bash
export YOSYS=/path/to/selected/yosys
export STA=/path/to/sta
export LIBERTY=/path/to/sky130_fd_sc_hd__tt_025C_1v80.lib
```

## Replay Commands

```bash
sha256sum -c SHA256SUMS
./replay_area.py
./replay_timing.py
./replay_equiv.sh
```

`replay_timing.py` consumes `gold_mapped.v` and `gate_mapped.v`, which are
produced by `replay_area.py`.

## Local Replay Receipt

Area under selected Yosys:

- Gold chip area: `10339.9168`
- Gate chip area: `10333.6608`
- Delta: `-0.0605%`

Timing under the selected 10 ns / 2 ns I/O proxy:

- Gold max data arrival: `8.13 ns`
- Gate max data arrival: `7.25 ns`
- Delta: `-0.88 ns` (`-10.8241%`)
- Gold WNS/TNS: `-0.13 / -5.66`
- Gate WNS/TNS: `0.00 / 0.00`

Formal replay:

- Engine: Yosys `0.66+181`
- Passes: `async2sync`, `equiv_simple -seq 5`, `equiv_induct -seq 32`,
  `equiv_status -assert`
- Local result: `411` `$equiv` cells proven, `0` unproven.

Toggle proxy:

- Gold toggles: `6117`
- Gate toggles: `6117`
- Delta: `0.0%`

## Independent Replay Result

An independent cold replay from this package's exact hashes confirmed all of:

1. `SOURCE_DIFF.patch` is limited to the `greater_equal_xor_shape` expression.
2. Selected-toolchain area improves: `10339.9168 -> 10333.6608`, `-0.0605%`.
3. Selected-convention timing improves: max data arrival `8.13 ns -> 7.25 ns`,
   WNS/TNS `-0.13 / -5.66 -> 0.00 / 0.00`.
4. Sequential equivalence replay proves all `411/411` `$equiv` cells from a clean
   run.
5. The deterministic toggle proxy remains flat.

## ATH-2924 Timing-Route Conversion Receipt

After the ATH-2924 OpenSTA/SDC timing route landed, this saved lead was replayed
through the route and recorded in `ath2924_public_replay_receipt.json`.

Formal evidence and measurements are deliberately separated:

- Formal evidence: Yosys sequential equivalence replay closed `411/411`
  `$equiv` cells with exit code `0` for the module replay artifacts.
- Area measurement: selected Yosys area improved `10339.9168 -> 10333.6608`
  (`-0.0605%`).
- Timing measurement: OpenSTA reported complete gold and gate WNS/TNS/max-delay
  fields, with gate timing meeting the replay policy (`WNS=0.00`, `TNS=0.00`,
  max delay `7.25 ns`).

This is still a selected-toolchain module replay artifact. It is not a
customer-ready claim, not a whole-core `ibex_top` result, not integrated RTL,
and not proof/customer authority expansion.
