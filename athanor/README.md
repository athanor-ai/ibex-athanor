# Athanor Optimized Ibex Frontier

This fork preserves Athanor's optimized Ibex RTL frontier and the public
receipts needed to inspect each optimization.

Current branch: `athanor/verified-ppa-frontier`

## Included RTL replacements

| Module | Transform | Status |
| --- | --- | --- |
| `rtl/ibex_alu.sv` | `bwlogic_or_from_xor_and` | Formal pass; Yosys 0.9 pinned area/toggle/timing receipts included. |
| `rtl/ibex_decoder.sv` | `decoder_multdiv_predicate_factor` | Formal pass; Yosys 0.9 pinned area/toggle/timing receipts included. |
| `rtl/ibex_compressed_decoder.sv` | `rlist_init_formula` | Formal pass; Yosys 0.9 pinned area/toggle/timing receipts included; cross-tool sensitivity recorded. |

## Evidence Layout

- `athanor/ppa_frontier/ibex_alu_bwlogic/`
  - Gate RTL, gold RTL, Lean receipt, formal receipt, area/power/timing
    receipts, and manifest.
- `athanor/ppa_frontier/ibex_decoder_predicate/`
  - Gate RTL, gold RTL, Lean receipt, formal receipt, area/power/timing
    receipts, and manifest.
- `athanor/ppa_frontier/ibex_compressed_decoder_rlist/`
  - Gate RTL, gold RTL, canonical formal receipt, Yosys 0.9 pinned
    area/toggle/timing receipts, cross-tool sensitivity note, and manifest.

This branch intentionally contains final public frontier artifacts only. Raw
runner logs, local filesystem paths, and internal workflow notes are excluded.
