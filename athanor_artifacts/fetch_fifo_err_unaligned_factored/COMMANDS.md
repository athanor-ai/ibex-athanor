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

The selected discovery lead numbers are recorded in `lead_manifest.json`:
generic cells 396 -> 395, liberty cells 456 -> 451, and toggle proxy
4008 -> 4008. The relation-aware sequential miter in `replay_equiv.sh`
is the formal closure for the FIFO occupancy relation that the first
canonical equivalence screen could not infer.
