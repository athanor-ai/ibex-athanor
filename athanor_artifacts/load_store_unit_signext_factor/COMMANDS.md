# Replay commands

Set:

```bash
export YOSYS=/path/to/pinned-yosys-0.66+181
export STA=sta
export LIBERTY=/path/to/sky130_fd_sc_hd__tt_025C_1v80.lib
```

Run:

```bash
sha256sum -c INPUT_SHA256SUMS
./replay_area.sh
./replay_timing.py
./replay_equiv.sh
./replay_toggle.py
sha256sum -c SHA256SUMS
```

`./replay_toggle.py` exits non-zero because the measured gate toggle count
regresses. That is the expected negative receipt for this candidate.
