# Athanor Ibex Results

Ibex is a real open-source 32-bit RISC-V CPU core. This fork publishes Athanor
Ibex optimization results. Every promoted row binds the exact RTL candidate to
metrics, proof or equivalence, activity checks, and replayable artifacts.

## Optimization Summary

- **Accepted public evidence:** five promoted artifacts: two whole-core
  `ibex_top` rows and three module-local rows. Whole-core claims are made only
  where the package carries an `ibex_top` receipt.
- **Whole-core reach:** `ibex_top / no_bp_prefetch_direct` improves selected
  toolchain area from `108441.5040` to `108373.9392`, keeps toggle activity
  flat at `311729 -> 311729`, and carries `1956/1956` Yosys equivalence plus
  hosted OSS-FV/cold-review evidence.
- **Second top-level row:** `ibex_if_stage / expanded_predicate_factor` reaches
  `ibex_top` with area `108428.9920 -> 108397.7120` (0.03% reduction), flat toggle activity, and
  cold replay.
- **Module-local timing result:** `ibex_multdiv_slow` improves max data-arrival
  from `8.13 ns` to `7.25 ns` with flat toggle activity and full formal replay.
- **Sequential proof coverage:** `ibex_fetch_fifo / err_unaligned_factored`
  carries relation-aware temporal induction and SBY/ABC PDR receipts, so the
  Ibex story is not only combinational equivalence.
- **Claim guard:** these are selected-toolchain, hash-bound, replayable
  receipts. They do not claim Synopsys/Cadence signoff, workload power, place
  and route closure, or additive whole-core benefit from module-local rows.

## Status

| Field | Status |
| --- | --- |
| Core | lowRISC Ibex |
| Evidence level | Five promoted artifacts: two whole-core rows and three module-local rows |
| Latest whole-core row | `ibex_top / no_bp_prefetch_direct` |
| Claim boundary | Whole-core claims require an `ibex_top` receipt. Module-local rows are not added together into a processor-level claim. |

## Promoted Evidence

| Target | Scope | Metric result | Correctness / activity receipt | Package |
| --- | --- | --- | --- | --- |
| `ibex_if_stage / expanded_predicate_factor` | Whole-core `ibex_top` | Area `108428.9920 -> 108397.7120` (0.03% reduction); recorded WNS groups improve | Toggle flat `311729 -> 311729`; Yosys equivalence `1956/1956`; cold replay `6/6` | [`if_stage_expanded_predicate_factor`](athanor_artifacts/if_stage_expanded_predicate_factor/) |
| `ibex_top / no_bp_prefetch_direct` | Whole-core `ibex_top` | Area `108441.5040 -> 108373.9392` (0.06% reduction); WNS deltas `+13.7942/+13.7942/+13.7924/+0.3407/+0.1761ns` | Toggle flat `311729 -> 311729`; Yosys equivalence `1956/1956`; hosted OSS-FV green; cold review passed | [top-level receipt](https://github.com/athanor-ai/ibex-athanor/blob/ea0e5bc50e2322369a5cee166161acadbda417f0/athanor_artifacts/if_stage_no_bp_prefetch_direct/top_level_first/top_level_first_receipt.json) |
| `ibex_multdiv_slow / greater_equal_xor_shape` | Module-local | Area `10339.9168 -> 10333.6608` (0.06% reduction); data arrival `8.13ns -> 7.25ns` (10.8% reduction) | Toggle flat `6117 -> 6117`; Yosys equivalence `411/411` | [`multdiv_slow_greater_equal_xor_shape`](athanor_artifacts/multdiv_slow_greater_equal_xor_shape/) |
| `ibex_multdiv_fast / greater_equal_xor_shape` | Module-local | Cell metric flat `3306 -> 3306`; max delay `10.85ns -> 10.57ns` (2.6% reduction) | Toggle flat `7657 -> 7657`; Yosys equivalence `772/772` | [`multdiv_fast_greater_equal_xor_shape`](athanor_artifacts/multdiv_fast_greater_equal_xor_shape/) |
| `ibex_fetch_fifo / err_unaligned_factored` | Module-local | Generic cells `396 -> 395` (0.3% reduction); liberty cells `456 -> 451` (1.1% reduction); timing flat at `6.32ns` | SAIF transition-count flat `34031 -> 34031`; relation-aware temporal induction and SBY/ABC PDR close; bad mutant fails | [`fetch_fifo_err_unaligned_factored`](athanor_artifacts/fetch_fifo_err_unaligned_factored/) |

## Proofs And Receipts

Proofs and replay receipts live inside the package linked from each row.

| Evidence | Where to look |
| --- | --- |
| Yosys equivalence | Package-local `equiv_yosys66.ys`, `replay_equiv_yosys66.ys`, `top_level_first/equiv.ys`, and matching `.log` files |
| Temporal induction / SBY PDR | `fetch_fifo_err_unaligned_factored/bounded_k*.log`, `relation_aware_seq_miter_manifest.json`, and `sby_abc_pdr_initzero/` |
| Activity and replay | `toggle_convention_receipt.json`, `top_level_first_receipt.json`, `ath2924_public_replay_receipt.json`, `SHA256SUMS`, and `python3 athanor/verify_public_receipts.py` |
| Lean / EBMC / CEGAR | Not claimed by these promoted rows unless a package explicitly carries that method's receipt |

## Evidence Ledger

Rejected, historical, and benchmark packages remain visible because they teach
the search, but they are not promoted results. Examples include `ibex_alu /
bwlogic_or_from_xor_and` as a timing tradeoff, `ibex_branch_predict /
candidate2` as an area reject, and the native-agent ablation as benchmark
evidence rather than a frontier claim.

## Evidence Bar

A promoted row requires:

1. Bounded RTL diff.
2. Selected-flow area and timing on the recorded toolchain.
3. Equivalence or hosted formal proof on the exact subject.
4. Toggle/activity check under the stated convention.
5. Replayable hashes plus non-author cold review.

## Replay

- Toolchain policy: [`athanor/toolchain_policy.json`](athanor/toolchain_policy.json)
- Receipt verifier: `python3 athanor/verify_public_receipts.py`
- Artifact packages: [`athanor_artifacts/`](athanor_artifacts/)
- Frontier receipt layout: [`athanor/ppa_frontier/`](athanor/ppa_frontier/)

Common receipt files include `SOURCE_DIFF.patch`, PPA JSON or reports,
equivalence scripts/logs, toggle/activity logs, `SHA256SUMS`, and `COMMANDS.md`.

## Upstream

The original lowRISC documentation, examples, and source tree are preserved. See
[`doc/`](doc/) and [`LICENSE`](LICENSE) for upstream terms.
