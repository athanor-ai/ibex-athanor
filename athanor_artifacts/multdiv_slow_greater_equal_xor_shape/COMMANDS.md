# Replay Commands

Set the selected toolchain paths:

```bash
export YOSYS=/path/to/selected/yosys
export STA=/path/to/sta
export LIBERTY=/path/to/sky130_fd_sc_hd__tt_025C_1v80.lib
```

Verify package hashes:

```bash
sha256sum -c SHA256SUMS
```

Replay area:

```bash
./replay_area.py
```

Replay timing after area mapping has produced `gold_mapped.v` and
`gate_mapped.v`:

```bash
./replay_timing.py
```

Replay sequential equivalence:

```bash
./replay_equiv.sh
```

Check the source-level transform:

```bash
git diff --no-index -- gold_source.sv gate_source.sv
```
