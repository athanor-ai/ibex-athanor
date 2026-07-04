# ATH-2686 Second-Design Prep

Status: prep only. This file does not select the second design and does not
claim any PPA result. It records the harness criteria and shortlist so Aidan can
choose the next target without losing the Ibex lessons from ATH-2699/ATH-2685.

## Why Pivot

The top-level-first Ibex loop found one accepted whole-core win:
`if_stage_expanded_predicate_factor`. The fixed detector pass over selected
Ibex elaboration now surfaces only that already-accepted lead and zero
spend-ready constant-propagation leads. Additional IF-stage/default-selected
candidates were non-additive against the accepted set, and the real non-default
RV32M candidate regressed at the cheap area gate.

The honest Ibex headline therefore remains the accepted #7 result:

- whole-core selected-toolchain area: `108428.9920 -> 108397.7120`
- area delta: `-0.02885%`
- timing: all recorded WNS groups improve
- formal: `1956/1956` cells proven
- toggle: `0.0%`
- independent cold replay: complete

The next growth lever is a second design with a different critical-path profile.
That grows the headline opportunity and tests whether the ATH-2685 detectors
generalize beyond Ibex.

## Selection Criteria

A candidate should satisfy all of these before becoming the committed
ATH-2686 target:

- Open-source RTL with license acceptable for public receipts.
- Yosys-friendly build path that can produce a stable top-level area report.
- A timing path we can measure with the selected open-source flow or a clearly
  documented substitute until the selected-flow harness is complete.
- A formal or equivalence path for candidate modules before any promotion.
- Toggle/activity harness path, or a small bounded harness we can make
  deterministic before claiming a win.
- Critical-path profile meaningfully different from Ibex IF-stage control.
- Detector reconnaissance that surfaces at least one plausible non-default,
  netlist-changing lead after selected-elaboration filtering.

## Shortlist

The machine-readable shortlist lives in
[`configs/ath2686_candidate_cores.json`](configs/ath2686_candidate_cores.json).

Current recommendation for first harness target, pending Aidan's choice:
PicoRV32. It is already available in the workspace, is compact enough for fast
iteration, has native Yosys/formal hooks, and the source-only ATH-2685 detector
finds a broad candidate set while correctly marking constant-prop rows as
requiring selected-elaboration residual evidence.

A prep-only PicoRV32 baseline probe is recorded in
[`configs/ath2686_picorv32_baseline.json`](configs/ath2686_picorv32_baseline.json).
It maps the unmodified core through the selected Yosys/Sky130 path and records
source, toolchain, liberty, log, and mapped-netlist hashes. This is not a design
commitment and not an optimization claim; it is only a reproducibility starting
point if PicoRV32 is selected.

The same file also records an M-extension selected-flow probe
(`ENABLE_FAST_MUL=1`, `ENABLE_DIV=1`) plus the first residual detector replay.
That replay found two residual shared-term rows, but both are cheap-kill rows:
one is assertion/formal-only (`0 == mem_wstrb`) and one is selected-flow area
neutral (`pcpi_rs1 - pcpi_rs2`, `32880.2848 -> 32880.2848`). Those rows are
evidence for the next ATH-2685 filter, not win candidates. No equivalence,
toggle, or cold replay is warranted until a candidate changes selected-flow
area/timing in the right direction.

The first reusable selected-flow harness is now
[`syn/picorv32_yosys66.sh`](../syn/picorv32_yosys66.sh), with the target config
in [`configs/picorv32_yosys66.json`](configs/picorv32_yosys66.json). It emits
the same report shape that `top_level_first.py` consumes for Ibex:
`reports/area.rpt` plus `reports/timing/{overall,reg2reg,reg2out,in2reg,in2out}.csv.rpt`.
The selected M-extension baseline is `145644.6848` area with WNS groups
`overall=-5.1590`, `reg2reg=-5.1590`, `reg2out=6.7483`, `in2reg=1.8232`,
and `in2out=7.7694`.
This is the area/timing half of the second-design harness only. Since PicoRV32
currently lives outside this repository under `/workdir/oss-demo-targets`, the
candidate patch/equivalence/toggle legs need a follow-up cross-repo artifact
step before any win can be promoted.

SERV and VexRiscv remain useful comparison targets because their microarchitectures
are deliberately different from Ibex, but they require fetch/license/toolchain
verification before commitment.

## First Harness Slice

The first ATH-2686 implementation slice should add only the reusable scaffolding:

1. Add a second core config shaped like `configs/ibex_top_yosys66.json`.
2. Add a target-specific synth wrapper that emits deterministic area/timing
   receipt paths.
3. Run `athanor/top_level_first.py` on a no-op patch and require a negative or
   neutral receipt with stable hashes.
4. Run ATH-2685 detector reconnaissance in source-only mode, then selected-flow
   residual mode once the synth wrapper emits an elaborated view.
5. Do not claim a win until the normal 5-point bar and independent cold replay
   both pass.

This keeps the next step in-lane for Lane 1: build the target-agnostic pipeline,
then feed real detector leads through it.
