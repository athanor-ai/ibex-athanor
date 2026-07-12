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

Replay selected-flow area:

```bash
./replay_area.py
```

Replay timing after area mapping has produced `gold_mapped.v` and
`gate_mapped.v`:

```bash
./replay_timing.py
```

Replay the output-equivalence SAT miter:

```bash
${YOSYS:-yosys} -s replay_output_miter_yosys66.ys
```

Replay the raw internal same-name `$equiv` check:

```bash
./replay_equiv.sh
```

The output miter is the formal evidence used by the public receipt. The raw
`$equiv` replay is included to document scope: it leaves 15 internal same-name
cells unclosed and must not be cited as a stronger internal-equivalence claim.
