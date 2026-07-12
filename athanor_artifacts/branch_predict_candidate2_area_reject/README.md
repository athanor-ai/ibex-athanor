# ibex_branch_predict candidate 2 selected-toolchain reject

This package records an honest rejection of a saved `ibex_branch_predict`
optimization lead after replay through the selected Yosys/OpenSTA flow.

Classification:
`honest_reject_selected_toolchain_area_regression_despite_timing_and_output_equiv`

This is not an optimization win. It is public evidence that the flow rejects a
candidate when the full selected-toolchain replay contradicts the earlier
pre-route signal.

## What Was Checked

The saved lead originally looked promising before the OpenSTA timing route was
available:

- early cell-count signal: `203 -> 191`, `-5.91%`
- early switching signal: `-29.66%`
- prior blocker: timing unavailable because the old path could not consume the
  generated SDC constraints

After the ATH-2924 timing route landed, the copied candidate artifact was
replayed through the selected flow:

- area measured with Yosys 0.66+181, ABC, and the pinned Sky130 liberty file
- timing measured with OpenSTA using the 10 ns clock / 2 ns I/O proxy
- output equivalence checked with a Yosys SAT miter

## Result

Area regressed after full mapping:

- Gold area: `1289.9872`
- Gate area: `1361.3056`
- Delta: `+5.5286%`

Timing was measured and met:

- Gold WNS/TNS/max delay: `-0.86 ns / -5.92 ns / 8.86 ns`
- Gate WNS/TNS/max delay: `0.00 ns / 0.00 ns / 7.15 ns`

Formal evidence:

- The output miter over `predict_branch_taken_o` and `predict_branch_pc_o`
  closed with Yosys SAT: exit code `0`, trigger unsat, `SUCCESS`.
- The raw internal same-name `$equiv` replay is not the acceptance leg for this
  package. It left `66/81` internal cells marked equivalent and `15` internal
  same-name cells unclosed. That scope note is part of the receipt.

Because selected-toolchain mapped area regressed, the candidate is rejected.

## Files

- `gold_source.sv`, `ibex_pkg.sv`: source context for the original module.
- `gate_source.v`: copied candidate gate artifact from the saved lead.
- `gold_elab.v`, `gate_elab.v`: elaborated replay artifacts used by the public
  scripts.
- `replay_area.py`: Yosys 0.66+181 + ABC + liberty area replay.
- `replay_timing.py`: OpenSTA timing replay.
- `replay_output_miter_yosys66.ys`: Yosys SAT output-miter replay.
- `replay_equiv_yosys66.ys`, `replay_equiv.sh`: raw internal `$equiv` replay
  kept to document the proof-scope caveat.
- `public_replay_receipt.json`: machine-readable public receipt.
- `INPUT_SHA256SUMS`: hashes for primary replay inputs.
- `SHA256SUMS`: hashes for the full public package.

## Boundary

This is a selected-toolchain replay artifact for a rejected module-level
candidate. It is not customer-ready, not integrated into main RTL, not an
optimizer acceptance change, not a whole-core `ibex_top` result, and not a
customer claim.

The useful product signal is falsifiability: the system measured a candidate it
previously had to save as timing-missing, then rejected it when the full mapped
area replay failed the acceptance bar.
