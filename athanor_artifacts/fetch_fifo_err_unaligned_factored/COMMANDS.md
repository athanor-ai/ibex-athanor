# Replay commands

Set the selected toolchain paths:

```bash
export YOSYS=/path/to/yosys-0.66+181
export STA=sta
export LIBERTY=/path/to/sky130_fd_sc_hd__tt_025C_1v80.lib
```

Run the public packet:

```bash
sha256sum -c SHA256SUMS
./replay_area.py
./replay_timing.py
./replay_equiv.sh
./replay_toggle.py
sha256sum -c SHA256SUMS
```

Check the source-level transform:

```bash
git diff --no-index -- gold_source.sv gate_source.sv
```

The corrected packet reports:

- `replay_area.py`: selected generic cells 396 -> 395 and selected liberty
  cells 456 -> 451.
- `replay_timing.py`: OpenSTA timing is flat at 6.32 ns with WNS/TNS 0.0.
- `replay_toggle.py`: primary replay toggle metric is SAIF transition-count
  sum 34031 -> 34031, delta 0.0%. The older discovery-probe counter
  4008 -> 4008 is retained in `lead_manifest.json` as historical probe
  context, not as a separate claim.
- `replay_equiv.sh`: relation-aware temporal-induction miter closes, the
  no-external-occupancy variant closes, and the bad mutant fails as the
  non-vacuity bite.

The old canonical `equiv_simple + equiv_induct` screen that left 1/454 cells
unproven is retained as prior evidence only. The active packet classification
is the relation-aware miter closure.
