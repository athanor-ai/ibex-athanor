# Athanor Ibex: Verifiable RISC-V Optimization

Ibex is a real open-source 32-bit RISC-V CPU core. This fork uses it as a
public testbed for a hard hardware problem: finding small RTL changes that
improve power, performance, or area without weakening correctness.

The goal is not to collect anecdotes. Every result here is tied to receipts:
selected-toolchain PPA, equivalence or formal proof, toggle/activity checks,
hash replay, and non-author review. If a row has not cleared that bar, it is
called a candidate, not a win.

## Current Status

| Topic | State |
| --- | --- |
| Accepted evidence | Five accepted rows have replayable receipts under the selected OSS CAD Suite 2026-06-30 / Yosys 0.66+181 baseline, including the routed PR #31 top-level survivor and the `ibex_fetch_fifo` module-local row. |
| Latest frontier result | PR #31, `ibex_top` / `no_bp_prefetch_direct`, remains the latest accepted top-level survivor. The latest accepted module-local row is `ibex_fetch_fifo` / `err_unaligned_factored`. |
| Tooling claim | Athanor/Kairos is used here as the measurement, filtering, replay, and evidence pipeline. This README does **not** claim autonomous discovery for #31. |
| Main gaps | Add machine-enforced proof-subject binding, make autonomous rediscovery reproducible, and broaden top-level survivors beyond one path family. |

## Evidence Bar

Promotion requires evidence for the exact claim:

1. Bounded RTL diff.
2. Selected-flow area and timing on the recorded toolchain.
3. Equivalence or hosted formal proof on the exact subject.
4. Toggle/activity check under the stated convention.
5. Replayable hashes plus non-author cold review.

Module-local movement is useful evidence, but whole-core claims require an
`ibex_top` receipt. Local wins are not added together without an integrated
top-level run.

## Results Snapshot

| Transform | Status | PPA signal | Correctness / activity | Receipt |
| --- | --- | --- | --- | --- |
| `ibex_multdiv_slow` / `greater_equal_xor_shape` | Accepted artifact | Area `10339.9168 -> 10333.6608`; data arrival `8.13ns -> 7.25ns` | Toggle flat `6117 -> 6117`; Yosys equiv `411/411` | [`athanor_artifacts/multdiv_slow_greater_equal_xor_shape/`](athanor_artifacts/multdiv_slow_greater_equal_xor_shape/) |
| `ibex_multdiv_fast` / `greater_equal_xor_shape` | Accepted artifact | Cell metric flat `3306 -> 3306`; max delay `10.85ns -> 10.57ns` | Toggle flat `7657 -> 7657`; Yosys equiv `772/772` | [`athanor_artifacts/multdiv_fast_greater_equal_xor_shape/`](athanor_artifacts/multdiv_fast_greater_equal_xor_shape/) |
| `ibex_if_stage` / `expanded_predicate_factor` | Accepted top-level artifact | `ibex_top` area `108428.9920 -> 108397.7120`; all recorded WNS groups improve | Toggle flat `311729 -> 311729`; Yosys equiv `1956/1956`; cold replay `6/6` | [`athanor_artifacts/if_stage_expanded_predicate_factor/`](athanor_artifacts/if_stage_expanded_predicate_factor/) |
| PR #31: `ibex_top` / `no_bp_prefetch_direct` | Accepted survivor | `ibex_top` area `108441.5040 -> 108373.9392`; WNS deltas `+13.7942/+13.7942/+13.7924/+0.3407/+0.1761ns` | Toggle flat `311729 -> 311729`; Yosys equiv `1956/1956`; hosted OSS-FV green; cold review passed | [#31 top-level selected-flow receipt](https://github.com/athanor-ai/ibex-athanor/blob/ea0e5bc50e2322369a5cee166161acadbda417f0/athanor_artifacts/if_stage_no_bp_prefetch_direct/top_level_first/top_level_first_receipt.json) |
| `ibex_fetch_fifo` / `err_unaligned_factored` | Accepted module-local artifact | Generic cells `396 -> 395`; liberty cells `456 -> 451` (`-1.0965%`); timing flat at `6.32ns` | SAIF transition-count flat `34031 -> 34031`; relation-aware temporal induction closes; relation-aware SBY/ABC PDR closes under explicit init-zero state relation; bad mutant fails | [`athanor_artifacts/fetch_fifo_err_unaligned_factored/`](athanor_artifacts/fetch_fifo_err_unaligned_factored/) and [`athanor/ppa_frontier/fetch_fifo_err_unaligned_factored/`](athanor/ppa_frontier/fetch_fifo_err_unaligned_factored/) |

## Latest Accepted Survivor: PR #31

`no_bp_prefetch_direct` specializes the instruction-fetch prefetch branch/address
path for the no-branch-predictor configuration. In that configuration,
`predict_branch_taken` is statically zero, so `branch_req = pc_set_i |
predict_branch_taken` collapses to `pc_set_i`. The branch-predictor path remains
intact when `BranchPredictor=1`.

The local package
[`athanor_artifacts/if_stage_no_bp_prefetch_direct/`](athanor_artifacts/if_stage_no_bp_prefetch_direct/)
records module-local precursor evidence. The accepted row above uses the
top-level PR #31 receipt because the claim is about `ibex_top`, not just
`ibex_if_stage`.

PR #31 is an accepted survivor on `master` because hosted OSS-FV proved the
candidate RTL and the cold review passed. It is still not an autonomous-discovery
claim: the structural insight was human-guided, while Athanor/Kairos supplied
the measurement, filtering, replay, and evidence chain.

## Latest Accepted Module-Local Discovery: fetch FIFO

`err_unaligned_factored` factors the `ibex_fetch_fifo` unaligned-error predicate.
The selected-toolchain public row records a liberty-mapped cell reduction
`456 -> 451` with timing and toggle flat. Correctness is carried by a
relation-aware sequential miter that derives FIFO occupancy from reset and
reachability, plus a distinct relation-aware SBY/ABC PDR replay under an
explicit init-zero state relation. A bad `err_unaligned` mutant fails the same
PDR replay, preserving the non-vacuity bite. This is a module-local row, not a
whole-core `ibex_top` claim or customer-ready RTL integration claim.

## Benchmarks

Benchmarks are replayable customer-facing evidence packages. They show what RTL
subject was tested, which property was evaluated, which proof method was used,
and where a customer can independently replay the result. Module-local
benchmarks do not imply a whole-core `ibex_top` claim.

| Benchmark | Module | What it tests | Proof method | Result | Replay |
| --- | --- | --- | --- | --- | --- |
| Fetch FIFO sequential equivalence | `ibex_fetch_fifo` | `err_unaligned_factored` preserves FIFO behavior under reset/state relation | Relation-aware temporal induction + SBY/ABC PDR; bad mutant fails | Cells `456 -> 451`; timing/toggle flat; `customer_claim_ready=false` | [`artifact`](athanor_artifacts/fetch_fifo_err_unaligned_factored/) |
| Native one-shot ablation | `ibex_fetch_fifo` | Frozen one-shot agents against the same FIFO optimization task | Same evidence bar after the raw answer; no Kairos loop or prior receipts | GPT-5.5 pilot captured; native-clean Opus 4.8 raw candidate captured (pending full replay); no frontier claim | [`artifact`](athanor_artifacts/ibex_fetch_fifo_native_agent_ablation/) |

## Latest ATH-2924 Timing-Route Replays

The ATH-2924 timing route adds a missing evidence step: saved structural leads
can now be replayed with complete OpenSTA gold and gate timing fields before
any acceptance language.

- `ibex_multdiv_slow` / `greater_equal_xor_shape` converted to a complete
  selected-toolchain module receipt. Yosys formal equivalence closed `411/411`
  `$equiv` cells; selected Yosys area improved `-0.0605%`; OpenSTA timing
  measured and met. This remains a module-level artifact, not an integrated
  whole-core result.
- `ibex_branch_predict` / candidate 2 was honestly rejected. Its early
  pre-route signal reported lower cell count and toggle activity, but full
  selected-toolchain replay measured area `1289.9872 -> 1361.3056`
  (`+5.5286%`). The output SAT miter closed and OpenSTA timing met, but area
  regression blocks acceptance.

The rejected package is public on purpose:
[`athanor_artifacts/branch_predict_candidate2_area_reject/`](athanor_artifacts/branch_predict_candidate2_area_reject/).
Publishing rejected receipts makes the acceptance bar inspectable; a candidate
that fails a required axis stays a rejection even when another axis improves.

## What This Shows

- Small RTL rewrites can move PPA on a real RISC-V core.
- The useful signal is multi-axis: area, timing, toggle, proof, and replay all
  matter.
- Some positive-looking edits are only tradeoffs or do not compose at top level.
- Today, Athanor/Kairos is strongest as an evidence pipeline; autonomous
  rediscovery is a separate gap to close with before/after receipts.

## Gaps And Next Work

1. Add proof-subject binding so a green formal row cannot prove the wrong RTL.
2. Teach the proposer to rediscover RISC-V optimization classes from RTL context.
3. Improve toggle/power coverage for each candidate's touched cone.
4. Broaden accepted top-level survivors beyond one path family.
5. Keep PPA constraint sets configurable for future customer targets.

## Audit Map

- Toolchain policy: [`athanor/toolchain_policy.json`](athanor/toolchain_policy.json)
- Receipt verifier: `python3 athanor/verify_public_receipts.py`
- Artifact packages: [`athanor_artifacts/`](athanor_artifacts/)
- Frontier receipt layout: [`athanor/ppa_frontier/`](athanor/ppa_frontier/)
- Flow scripts and tests: [`athanor/`](athanor/) and [`syn/`](syn/)

Common receipt files:

- `SOURCE_DIFF.patch` or gate source: bounded RTL change.
- `top_level_ppa_yosys66.json`, `area*.json`, or `reports/`: PPA data.
- `equiv_yosys66.ys` and `equiv_yosys66.log`: equivalence replay.
- `logs/convention_v1/`: toggle/activity receipt and traces.
- `SHA256SUMS`: package hash binding.
- `COMMANDS.md`: replay commands where available.

## Historical And Rejected Rows

Rejected rows stay visible because they teach the search:

- `ibex_alu` / `bwlogic_or_from_xor_and` saves area and cells but worsens timing,
  so it is a tradeoff row, not a full-PPA win.
- `ibex_branch_predict` / candidate 2 passes the output SAT miter and meets
  OpenSTA timing, but mapped selected-toolchain area regresses, so it is an
  honest reject rather than an optimization artifact.
- `ibex_id_stage` / `no_wb_prio_assign` and `ibex_load_store_unit` /
  `signext_factor` showed positive area, timing, and Yosys-equivalence signals
  but regressed toggle/activity.
- `ibex_compressed_decoder` / `rlist_init_formula` is historical evidence under
  an older Yosys 0.9 recipe and is not part of the current selected-toolchain
  frontier.

## Upstream Ibex

The original lowRISC documentation, examples, and source tree are preserved.
Start with [`doc/`](doc/) for the upstream Ibex manual and [`LICENSE`](LICENSE)
for license terms.
