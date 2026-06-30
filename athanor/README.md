# Athanor Ibex Frontier Receipts

This directory contains public receipts for Athanor's optimized Ibex RTL. The
artifacts tie each optimized module to formal equivalence evidence, machine
checked helper proofs, and area, switching, and timing measurements under a
pinned open-source toolchain.

## Results Summary

| Module | Transform | Status |
| --- | --- | --- |
| `rtl/ibex_alu.sv` | `bwlogic_or_from_xor_and` | Formal pass; Yosys 0.9 pinned area/toggle/timing receipts included. Mapped-cell delta: `-6.77%`. |
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
- `athanor/ppa_frontier/ibex_compressed_decoder_rlist/`
  - Gate RTL, gold RTL, canonical formal receipt, Yosys 0.9 pinned
    area/toggle/timing receipts, cross-tool sensitivity note, and manifest.

Additional archived receipt rows may appear under `ppa_frontier/` when they
carry complete public manifests, but the top-level README lists the current
customer-facing frontier.
