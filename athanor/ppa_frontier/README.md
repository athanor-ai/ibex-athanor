# PPA Frontier Receipts

This directory stores replay artifacts for optimized Ibex modules.

Each module directory should include:

- optimized gate RTL
- original/gold RTL when available
- formal receipt
- area, power/toggle, and timing receipts
- Lean or other proof receipts when available
- manifest with artifact hashes

Only rows that pass the current verification bar should be added here.
PPA-positive filters with incomplete formal proof belong in the research
ledger, not in this frontier branch.

## Current Rows

| Module | Transform | Contract | Public status |
| --- | --- | --- | --- |
| `ibex_alu` | `bwlogic_or_from_xor_and` | `area_tradeoff_yosys66` | Area-positive selected-toolchain tradeoff; timing regresses. |
| `ibex_compressed_decoder` | `rlist_init_formula` | `cross_tool_sensitive_rebaseline_pending` | Historical cross-tool-sensitive evidence; selected-toolchain rebaseline pending. |
| `ibex_fetch_fifo` | `err_unaligned_factored` | `module_full_ppa_yosys66` | Accepted module-local selected-toolchain PPA row: area positive, timing flat, toggle flat, relation-aware miter closed with mutant bite. |

The selected public replay baseline is defined by
[`../toolchain_policy.json`](../toolchain_policy.json). Run
`python3 athanor/verify_public_receipts.py` from the repository root before
publishing updates. The verifier checks manifest hashes, selected-toolchain
status, selected row contracts, and public wording boundaries.

Rows with synthesis-flow sensitivity must pin the exact accepted toolchain and
record divergent toolchain results in their public receipts. They are not
portable synthesis-flow claims.
