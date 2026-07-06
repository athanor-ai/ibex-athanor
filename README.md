# Athanor Ibex: Verifiable RISC-V PPA Optimization

Ibex is a real, open-source 32-bit RISC-V CPU core. That makes it a useful
public target for a hard problem: improving chip power, performance, and area
without breaking correctness. Small RTL edits can look good under one synthesis
metric and still fail timing, increase switching activity, or subtly change
processor behavior. This fork records bounded optimization experiments together
with the evidence needed to audit them: selected-toolchain PPA, equivalence or
formal proof, toggle/activity checks, replay hashes, and cold review.

Read this repository as a research artifact first and an audit package second.
The high-level question is simple: can Athanor/Kairos help identify, measure,
and verify real micro-architectural improvements on a production-quality RISC-V
core? The answer today is: we have accepted artifact evidence for several
bounded transforms, one active frontier candidate waiting on hosted formal
verification, and clear gaps before broader autonomous discovery can be claimed.

## One-Screen Status

| Topic | Current state |
| --- | --- |
| Accepted evidence | Three accepted artifact rows are packaged under the selected OSS CAD Suite 2026-06-30 / Yosys 0.66+181 baseline. |
| Active frontier | PR #31, `ibex_top` / `no_bp_prefetch_direct`, is the current top-level selected-flow candidate. It has positive area/timing/equiv/toggle receipts, but it is **not accepted** until hosted OSS-FV terminals green and cold review passes. |
| Tooling role | Kairos/Athanor provides the measurement, filtering, replay, and evidence pipeline. Current README claims are evidence claims, not autonomous-discovery claims. |
| Main gap | Turn candidate evidence into accepted evidence only when the full bar closes: hosted formal proof, top-level replay, toggle/activity, pinned tools, and non-author review. |

## Evidence Standard

An optimization is promoted only when the evidence matches the claim. The normal
bar is:

1. **Bounded RTL diff:** the source change is small enough to review.
2. **Selected-flow PPA:** area and timing are measured under the recorded
   selected toolchain, not an ambient local setup.
3. **Correctness proof:** Yosys equivalence or hosted formal verification closes
   on the exact artifacts being discussed.
4. **Toggle/activity check:** switching does not regress under the stated
   convention.
5. **Replayability:** SHA-256 manifests, command notes, and independent cold
   replay make the result reproducible.

Module-local wins are not added together. Aggregate whole-core claims require a
separate integrated top-level run because synthesis interactions can erase or
change local improvements.

## Current Results

These are the rows a hardware engineer can audit directly from this tree, plus
the live #31 frontier receipt linked to its exact PR head until that package is
merged.

| Transform | Status | What moved | Correctness / activity | Receipt |
| --- | --- | --- | --- | --- |
| `ibex_multdiv_slow` / `greater_equal_xor_shape` | Accepted artifact | Area `10339.9168 -> 10333.6608` (`-0.0605%`); max data arrival `8.13ns -> 7.25ns` (`-0.88ns / -10.8241%`) | Toggle flat `6117 -> 6117`; Yosys equiv `411/411` proven | [`athanor_artifacts/multdiv_slow_greater_equal_xor_shape/`](athanor_artifacts/multdiv_slow_greater_equal_xor_shape/) |
| `ibex_multdiv_fast` / `greater_equal_xor_shape` | Accepted artifact | Cell metric flat `3306 -> 3306`; max delay `10.85ns -> 10.57ns` (`-0.28ns / -2.58%`) | Toggle flat `7657 -> 7657`; Yosys equiv `772/772` proven | [`athanor_artifacts/multdiv_fast_greater_equal_xor_shape/`](athanor_artifacts/multdiv_fast_greater_equal_xor_shape/) |
| `ibex_if_stage` / `expanded_predicate_factor` | Accepted top-level artifact | Whole-core `ibex_top` area `108428.9920 -> 108397.7120` (`-0.02885%`); all recorded WNS groups improve, including reg2reg `+13.8626ns` | Toggle flat `311729 -> 311729`; Yosys equiv `1956/1956`; independent cold replay `6/6` exact | [`athanor_artifacts/if_stage_expanded_predicate_factor/`](athanor_artifacts/if_stage_expanded_predicate_factor/) |
| PR #31: `ibex_top` / `no_bp_prefetch_direct` | Candidate only | Whole-core `ibex_top` area `108441.5040 -> 108373.9392` (`-0.06231%`); WNS deltas `+13.7942/+13.7942/+13.7924/+0.3407/+0.1761ns` across overall/reg2reg/reg2out/in2reg/in2out | Toggle flat `311729 -> 311729`; Yosys equiv `1956/1956`; hosted OSS-FV and cold review still required | [#31 top-level selected-flow receipt](https://github.com/athanor-ai/ibex-athanor/blob/12233fcfe681107e61d5dd3ad0694eaaf8f157c9/athanor_artifacts/if_stage_no_bp_prefetch_direct/top_level_first/top_level_first_receipt.json) |

### The Active Frontier Candidate

The `no_bp_prefetch_direct` candidate specializes the instruction-fetch prefetch
branch/address path for the default no-branch-predictor configuration. In that
configuration, `predict_branch_taken` is statically zero, so `branch_req =
pc_set_i | predict_branch_taken` collapses to `pc_set_i`. The candidate keeps
the branch-predictor path intact when `BranchPredictor=1` and simplifies only
the no-predictor path.

The local package
[`athanor_artifacts/if_stage_no_bp_prefetch_direct/`](athanor_artifacts/if_stage_no_bp_prefetch_direct/)
records the module-local precursor evidence. The active frontier claim uses the
top-level selected-flow receipt on PR #31, linked in the table above, because
whole-core PPA must be audited at `ibex_top`.

That is promising, but still candidate evidence. It must not be described as an
accepted RISC-V win until the hosted open-source formal-verification run
terminals green on the exact head and the non-author cold review passes.

## What We Have Learned

- Small RTL rewrites can produce measurable movement on a real RISC-V core, but
  the useful signal is multi-axis: area, timing, toggle, and proof all matter.
- Some changes are real tradeoffs rather than wins. A row with area savings and
  timing loss belongs in the research ledger, not in customer headline language.
- Some local wins do not compose. Whole-core synthesis can change the result, so
  each stacked or integrated claim needs its own selected-flow receipt.
- Kairos is currently strongest as an evidence and filtering pipeline. Teaching
  the proposer to rediscover these classes autonomously is a separate active
  improvement path and should not be conflated with the accepted artifact rows.

## Current Gaps And Next Improvements

1. **Close the hosted formal leg for the frontier candidate.** The next
   acceptance milestone is OSS-FV green plus cold review for
   `no_bp_prefetch_direct`.
2. **Improve autonomous discovery.** Feed the accepted and candidate patterns
   back into Kairos so the proposer can rediscover RISC-V optimization classes
   from RTL context, then record before/after rediscovery receipts.
3. **Broaden top-level survivors.** Keep searching for candidates that survive
   `ibex_top` selected-flow PPA, not just module-local synthesis.
4. **Tighten power and toggle coverage.** Make each candidate's touched cone
   exercised by the toggle convention, and avoid waivers when a better
   convention is needed.
5. **Keep customer constraints explicit.** Future customers may prefer different
   points on the PPA surface. Constraint sets should be configurable, and
   conditional/Pareto rows should stay separate from accepted wins.

## Evidence Map

Useful audit entry points:

- Selected toolchain policy:
  [`athanor/toolchain_policy.json`](athanor/toolchain_policy.json)
- Public receipt verifier:
  `python3 athanor/verify_public_receipts.py`
- Accepted and candidate artifact packages:
  [`athanor_artifacts/`](athanor_artifacts/)
- Public frontier receipt layout:
  [`athanor/ppa_frontier/`](athanor/ppa_frontier/)
- Candidate replay helpers and selected-flow scripts:
  [`athanor/`](athanor/) and [`syn/`](syn/)

Typical files inside an artifact package:

- `SOURCE_DIFF.patch` or gate source: bounded source change.
- `area*.json`, `top_level_ppa_yosys66.json`, or raw `reports/`: PPA receipt.
- `equiv_yosys66.ys` and `equiv_yosys66.log`: equivalence replay.
- `logs/convention_v1/`: toggle/activity convention receipt and traces.
- `SHA256SUMS`: hash manifest binding the package.
- `COMMANDS.md`: replay commands and cold-review notes where available.

## Appendix: Tradeoffs, Rejects, And Historical Rows

Rows that do not meet the full bar remain visible because they are useful
engineering evidence:

- `ibex_alu` / `bwlogic_or_from_xor_and` saves area and cells
  (`-6.3801%` area, `50` cells saved) but worsens timing (`+1.73ns /
  +19.59%`). It is a tradeoff row, not a full-PPA win.
- `ibex_id_stage` / `no_wb_prio_assign` and `ibex_load_store_unit` /
  `signext_factor` both showed positive area/timing/formal signals but regressed
  toggle/activity, so they are rejected for promotion.
- `ibex_compressed_decoder` / `rlist_init_formula` remains useful historical
  evidence under an older Yosys 0.9 recipe, but cross-tool sensitivity keeps it
  out of the current selected-toolchain frontier until replayed and reviewed
  under the public policy.

## Upstream Ibex

The original lowRISC documentation, examples, and source tree are preserved in
this repository. Start with [`doc/`](doc/) for the upstream Ibex manual and
[`LICENSE`](LICENSE) for license terms.
