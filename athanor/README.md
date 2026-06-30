# Athanor Optimized Ibex Frontier

This fork preserves Athanor's verified Ibex PPA frontier and the replay
receipts needed to reconstruct each optimization.

Current branch: `athanor/verified-ppa-frontier`

## Included RTL replacements

| Module | Transform | Status |
| --- | --- | --- |
| `rtl/ibex_alu.sv` | `bwlogic_or_from_xor_and` | Cross-agent verified local frontier; not customer-claim-ready until managed optimize/checkpoint replay closes. |
| `rtl/ibex_decoder.sv` | `decoder_multdiv_predicate_factor` | Replay package marks `customer_claim_ready=true`. |
| `rtl/ibex_compressed_decoder.sv` | `rlist_init_formula` | Canonical formal closed and Yosys 0.9 pinned full-PPA positive; cross-tool sensitive and not a portable synthesis-flow claim. |

## Evidence Layout

- `athanor/ppa_frontier/ibex_alu_bwlogic/`
  - Gate RTL, gold RTL, Lean receipt, formal receipt, area/power/timing
    receipts, evidence JSON, and replay summary.
- `athanor/ppa_frontier/ibex_decoder_predicate/`
  - Gate RTL, gold RTL, source bundle, Lean receipt, formal receipt,
    area/power/timing receipts, evidence JSON, and replay summary.
- `athanor/ppa_frontier/ibex_compressed_decoder_rlist/`
  - Gate RTL, gold RTL, canonical formal receipt, Yosys 0.9 pinned
    area/toggle/timing receipts, cross-tool sensitivity note, evidence JSON,
    and replay summary.

## Explicit Non-Frontier Rows

The following local leads are intentionally not applied to this branch:

- `ibex_multdiv_slow next_quotient_or_mask`: formal harness incomplete.
- `ibex_load_store_unit data_be_shift_formula`: formal harness incomplete.
- `ibex_pmp basic_perm_dynamic_index`: PPA regresses in the canonical flow.

Use the replay packages and manifests before promoting any additional RTL
change into this branch.
