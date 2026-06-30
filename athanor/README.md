# Athanor Optimized Ibex Frontier

This fork starts from the industry-standard lowRISC Ibex RTL and preserves
Athanor's formally checked RTL optimization frontier. The public artifacts in
this branch show the optimized modules, their original comparison points, and
the receipts used to evaluate functional equivalence plus area, switching, and
timing under a pinned open-source toolchain.

Current branch: `athanor/verified-ppa-frontier`

## Results Summary

| Module | Transform | Status |
| --- | --- | --- |
| `rtl/ibex_alu.sv` | `bwlogic_or_from_xor_and` | Formal pass; Yosys 0.9 pinned area/toggle/timing receipts included. Mapped-cell delta: `-6.77%`. |
| `rtl/ibex_decoder.sv` | `decoder_multdiv_predicate_factor` | Formal pass; Yosys 0.9 pinned area/toggle/timing receipts included. Liberty-cell delta: `-4.63%`. |
| `rtl/ibex_compressed_decoder.sv` | `rlist_init_formula` | Formal pass; Yosys 0.9 pinned area/toggle/timing receipts included. Chip-area delta: `-2.38%` in the canonical replay, with independent Yosys 0.9 replay at `-3.11%`. Cross-tool sensitivity is recorded. |

## Methodology

Each frontier row is kept as a bounded RTL transform rather than a broad module
rewrite. The public receipt set records:

- original/gold RTL and optimized gate RTL
- formal equivalence result and proved output/property scope
- Lean theorem receipt when a machine-checked helper identity is part of the
  transform rationale
- Yosys 0.9 pinned area result against the recorded liberty file
- toggle and OpenSTA timing proxy measurements
- SHA-256 manifest tying the public files to the receipt row

Rows with synthesis-flow sensitivity pin the accepted toolchain and record the
divergent toolchain result. They should be read as pinned-toolchain evidence,
not as portable claims across all synthesis flows.

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
