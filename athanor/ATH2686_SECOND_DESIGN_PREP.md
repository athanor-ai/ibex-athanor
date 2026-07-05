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

A refreshed replay with the ATH-2685 detector from athanor-kairos main
`73f6b5b1` used the selected-flow generated STA netlist as the elaborated
source. It returned the same two residual shared-term rows and zero residual
constant-propagation rows. That means PicoRV32 is currently a harness/proof of
transferability, not an optimization-spend surface: the detector has no
selected-flow, netlist-changing lead to promote into equivalence/toggle spend.

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
config sets `patch_root` to that checkout so `top_level_first.py` can apply and
restore candidate patches there while keeping this repository clean. The
receipt also preserves selected-flow generated artifacts (`picorv32_mapped.v`,
`picorv32_sta.v`, and the generated Yosys/OpenSTA scripts) under
`generated/{baseline,gate}/`, giving residual detector replay and cold replay a
pinned elaborated view. The equivalence/toggle legs still need a follow-up
cross-repo artifact step before any win can be promoted.

SERV now has a selected-flow baseline receipt in
[`configs/ath2686_serv_baseline.json`](configs/ath2686_serv_baseline.json), with
the target config in [`configs/serv_yosys66.json`](configs/serv_yosys66.json) and
the synth script in [`syn/serv_yosys66.sh`](../syn/serv_yosys66.sh). The
unmodified `serv_synth_wrapper` baseline maps to `8114.0320` area with WNS
groups `overall=4.0592`, `reg2reg=4.0592`, `reg2out=6.5025`, `in2reg=5.9589`,
and `in2out=7.9453`. That receipt is also harness-only: no transform has been
applied, and no formal, toggle, cold replay, or optimization-win claim exists.
The selected-flow residual detector replay against `athanor-kairos` main
`d4a44892` scanned all 18 SERV RTL files with the generated STA netlist as the
elaborated view and returned zero residual shared-term or constant-propagation
leads. That makes SERV a useful negative transferability receipt for the current
ATH-2685 families, but not an optimization-spend surface.

ultraembedded/riscv also has a selected-flow baseline receipt in
[`configs/ath2686_ultraembedded_riscv_baseline.json`](configs/ath2686_ultraembedded_riscv_baseline.json),
with the target config in
[`configs/ultraembedded_riscv_yosys66.json`](configs/ultraembedded_riscv_yosys66.json)
and the synth script in
[`syn/ultraembedded_riscv_yosys66.sh`](../syn/ultraembedded_riscv_yosys66.sh).
The unmodified `riscv_core` baseline maps to `187985.2928` area with WNS groups
`overall=-20.2890`, `reg2reg=-20.2293`, `reg2out=-8.2176`, `in2reg=-20.2890`,
and `in2out=-8.2773`. Source-only detector replay found 12 constant-prop rows,
but selected-flow residual replay returned zero leads. That makes it a second
negative transferability receipt for the current ATH-2685 families, while
preserving a direct-Verilog customer-relevant baseline for future detector work.

CV32E40P now has a bounded frontend/recon receipt in
[`configs/ath2686_cv32e40p_recon.json`](configs/ath2686_cv32e40p_recon.json),
with the target config in
[`configs/cv32e40p_recon.json`](configs/cv32e40p_recon.json) and the reproducible
frontend script in [`syn/cv32e40p_recon.sh`](../syn/cv32e40p_recon.sh). The
script converts the upstream lint-wrapper configuration with `sv2v`, then runs
only Yosys hierarchy/proc/opt/fsm/memory frontend passes before mapping. That
bounded stage is intentional: a scratch full-core selected-flow run progressed
through frontend elaboration but exceeded the cheap scout budget during ABC
mapping of `cv32e40p_mult`, so no full area/timing comparator is claimed.

The detector signal is different from the dry targets above. A current
`kairos-rtl-rewrite` replay over 31 files found 33 source-only leads. Supplying
the generated Yosys frontend netlist as the elaborated view filters
constant-prop leads to zero and removes the prior `cv32e40p_sleep_unit.sv`
formal/SVA false positives. Only two source-level shared-term leads remain, both
in `cv32e40p_load_store_unit.sv`.

The remaining load-store-unit datapath lead has a bounded module profile in
[`configs/ath2686_cv32e40p_lsu_profile.json`](configs/ath2686_cv32e40p_lsu_profile.json),
generated by
[`syn/cv32e40p_lsu_shared_term_profile.sh`](../syn/cv32e40p_lsu_shared_term_profile.sh).
It factors the repeated `data_sign_ext_q` equality predicates and runs generic
Yosys synthesis on `cv32e40p_load_store_unit` only. The profile is area-neutral:
`987 -> 987` cells, so it does not clear the cheap pre-spend bar. No
equivalence, toggle, cold replay, full-core PPA, or headline language is
warranted for this candidate.

That closes the current CV32E40P pass under the ATH-2685 shared-term and
constant-prop families: the formal/SVA filter works on a second design, but no
candidate from those families survives the cheap pre-spend bar. New detector
families still need bounded profiling before any CV32E40P equivalence/toggle
spend.

A first new-family scout checked common-guard output gating in
`cv32e40p_decoder.sv` (`deassert_we_i ? default : signal` repeated across
decoder outputs). The bounded module profile is recorded in
[`configs/ath2686_cv32e40p_common_guard_profile.json`](configs/ath2686_cv32e40p_common_guard_profile.json).
It rewrites only the zero-default outputs to share `~deassert_we_i`; generic
Yosys maps baseline and gate to the same 1194 cells with the same cell-type
breakdown. That family is also a dry scout for now: do not build a detector or
spend equivalence/toggle until a stronger selected-flow signal appears.

A second new-family scout checked register-file write-enable guard factoring in
`cv32e40p_register_file_latch.sv`. The bounded module profile is recorded in
[`configs/ath2686_cv32e40p_regfile_guard_profile.json`](configs/ath2686_cv32e40p_regfile_guard_profile.json).
It factors the repeated `(we_*_i == 1'b1)` guards before the generated
onehot write-address decoders. Under the selected Yosys 0.66 toolchain, the
profile regresses by one generic cell (`4010 -> 4011`), so this family fails
the cheap pre-spend bar. No equivalence, toggle, cold replay, full-core PPA, or
headline language is warranted for this candidate.

A third new-family scout checked id-stage RAW forwarding hazard-tail factoring
in `cv32e40p_id_stage.sv`. The bounded module profile is recorded in
[`configs/ath2686_cv32e40p_idstage_hazard_tail_profile.json`](configs/ath2686_cv32e40p_idstage_hazard_tail_profile.json)
and replayed by
[`syn/cv32e40p_idstage_hazard_tail_profile.sh`](../syn/cv32e40p_idstage_hazard_tail_profile.sh).
It factors the repeated operand-used and nonzero-register guards into
`rega_forward_live`, `regb_forward_live`, and `regc_forward_live` before the
EX/WB/ALU forwarding comparisons. Under the selected Yosys 0.66 toolchain, the
bounded profile improves generic module cells (`14959 -> 14917`, with the
local `cv32e40p_id_stage` section `3274 -> 3232`). This is the first
CV32E40P bounded-positive scout, but it is not an optimization claim. The next
gate is a selected-flow/full-core cheap check; no formal, toggle, cold replay,
full-core PPA, accepted-win language, or headline language is warranted until
aggregate area/timing clears.

VexRiscv now has a generator-toolchain preflight receipt in
[`configs/ath2686_vexriscv_preflight.json`](configs/ath2686_vexriscv_preflight.json).
The checkout is present at git head `680756065e9e6fc50d8c3d6c58191a16e867d822`
with an MIT license, Scala `2.12.18`, SpinalHDL `1.13.0`, and SBT `1.6.0`
recorded from the repo files. That makes it a useful comparison target because
its configurable plugin pipeline is deliberately different from Ibex, but it is
not selected-flow ready yet: this container has no `java`, `sbt`, or `mill`, and
the checked-in `.v` files are board wrappers or test memory images, not generated
CPU RTL. The next VexRiscv step is generator-pinned RTL emission
(`GenFull`, `GenSmallest`, or a chosen deterministic config), then normal
selected-flow baseline and detector replay. No synthesis, PPA, formal, toggle,
cold replay, or optimization claim exists for VexRiscv at this stage.

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
