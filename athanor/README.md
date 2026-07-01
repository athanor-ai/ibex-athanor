# Athanor Ibex Frontier Receipts

This directory contains public receipts for Athanor's optimized Ibex RTL. The
artifacts tie each optimized module to formal equivalence evidence, machine
checked helper proofs, and area, switching, and timing measurements. The
current customer-facing area baseline is OSS CAD Suite 2026-06-30 / Yosys
0.66+181. Older Yosys 0.9 receipts are retained as historical reproducibility
and cross-tool sensitivity evidence.

## Results Summary

| Module | Transform | Status |
| --- | --- | --- |
| `rtl/ibex_alu.sv` | `bwlogic_or_from_xor_and` | Formal pass; Yosys 0.66+181 area replay is positive: `5471.4976 -> 5122.4128` chip area, `-6.38%`. Historical 0.9 toggle/timing receipts are included; 0.66 toggle/timing replay is pending. |
| `rtl/ibex_compressed_decoder.sv` | `rlist_init_formula` | Formal pass; historical Yosys 0.9 replay is positive, but Yosys 0.45 replay regressed. Current customer-facing 0.66 replay is pending independent area/toggle/timing closure. |

## Methodology

Each frontier row is kept as a bounded RTL transform rather than a broad module
rewrite. The public receipt set records:

- original/gold RTL and optimized gate RTL
- formal equivalence result and proved output/property scope
- Lean theorem receipt when a machine-checked helper identity is part of the
  transform rationale
- selected-toolchain area result against the recorded liberty file
- toggle and OpenSTA timing proxy measurements
- SHA-256 manifest tying the public files to the receipt row

Rows with synthesis-flow sensitivity record each divergent toolchain result and
are not promoted as customer-facing frontier rows until the selected baseline
area, toggle, timing, and independent replay receipts are complete.

## Evidence Layout

- `athanor/ppa_frontier/ibex_alu_bwlogic/`
  - Gate RTL, gold RTL, Lean receipt, formal receipt, area/power/timing
    receipts, Yosys 0.66 area receipt, and manifest.
- `athanor/ppa_frontier/ibex_compressed_decoder_rlist/`
  - Gate RTL, gold RTL, canonical formal receipt, historical Yosys 0.9
    area/toggle/timing receipts, cross-tool sensitivity note, and manifest.

Additional archived receipt rows may appear under `ppa_frontier/` when they
carry complete public manifests, but the top-level README lists the current
customer-facing frontier.
