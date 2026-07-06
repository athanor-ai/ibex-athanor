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
| Accepted evidence | Three packaged artifact rows have replayable receipts under the selected OSS CAD Suite 2026-06-30 / Yosys 0.66+181 baseline. |
| Frontier candidate | PR #31, `ibex_top` / `no_bp_prefetch_direct`, has positive top-level PPA/equiv/toggle evidence. It is **not accepted** until hosted OSS-FV terminals green on the candidate RTL and cold review passes. |
| Tooling claim | Athanor/Kairos is used here as the measurement, filtering, replay, and evidence pipeline. This README does **not** claim autonomous discovery for #31. |
| Main gaps | Close hosted formal proof for #31, make autonomous rediscovery reproducible, and broaden top-level survivors beyond one path family. |

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
| PR #31: `ibex_top` / `no_bp_prefetch_direct` | Candidate only | `ibex_top` area `108441.5040 -> 108373.9392`; WNS deltas `+13.7942/+13.7942/+13.7924/+0.3407/+0.1761ns` | Toggle flat `311729 -> 311729`; Yosys equiv `1956/1956`; hosted OSS-FV and cold review still required | [#31 top-level selected-flow receipt](https://github.com/athanor-ai/ibex-athanor/blob/50c1bf840199d0e6a197d355f35579d7340e1335/athanor_artifacts/if_stage_no_bp_prefetch_direct/top_level_first/top_level_first_receipt.json) |

## Active Frontier: PR #31

`no_bp_prefetch_direct` specializes the instruction-fetch prefetch branch/address
path for the no-branch-predictor configuration. In that configuration,
`predict_branch_taken` is statically zero, so `branch_req = pc_set_i |
predict_branch_taken` collapses to `pc_set_i`. The branch-predictor path remains
intact when `BranchPredictor=1`.

The local package
[`athanor_artifacts/if_stage_no_bp_prefetch_direct/`](athanor_artifacts/if_stage_no_bp_prefetch_direct/)
records module-local precursor evidence. The live frontier row above uses the
top-level PR #31 receipt because the claim is about `ibex_top`, not just
`ibex_if_stage`.

PR #31 is still candidate evidence. It becomes an accepted RISC-V result only if
hosted OSS-FV proves the candidate RTL on the exact head and the cold review
passes.

## What This Shows

- Small RTL rewrites can move PPA on a real RISC-V core.
- The useful signal is multi-axis: area, timing, toggle, proof, and replay all
  matter.
- Some positive-looking edits are only tradeoffs or do not compose at top level.
- Today, Athanor/Kairos is strongest as an evidence pipeline; autonomous
  rediscovery is a separate gap to close with before/after receipts.

## Gaps And Next Work

1. Finish #31 hosted formal proof and cold review.
2. Add proof-subject binding so a green formal row cannot prove the wrong RTL.
3. Teach the proposer to rediscover RISC-V optimization classes from RTL context.
4. Improve toggle/power coverage for each candidate's touched cone.
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
- `ibex_id_stage` / `no_wb_prio_assign` and `ibex_load_store_unit` /
  `signext_factor` showed positive area/timing/formal signals but regressed
  toggle/activity.
- `ibex_compressed_decoder` / `rlist_init_formula` is historical evidence under
  an older Yosys 0.9 recipe and is not part of the current selected-toolchain
  frontier.

## Upstream Ibex

The original lowRISC documentation, examples, and source tree are preserved.
Start with [`doc/`](doc/) for the upstream Ibex manual and [`LICENSE`](LICENSE)
for license terms.
