# Athanor Ibex Frontier Receipts

This directory contains public receipts for Athanor's optimized Ibex RTL. The
artifacts tie each optimized module to formal equivalence evidence, machine
checked helper proofs, and area, switching, and timing measurements. The
current customer-facing area baseline is OSS CAD Suite 2026-06-30 / Yosys
0.66+181. Older Yosys 0.9 receipts are retained as historical reproducibility
and cross-tool sensitivity evidence. The selected baseline is codified in
[`toolchain_policy.json`](toolchain_policy.json), and
[`verify_public_receipts.py`](verify_public_receipts.py) enforces that
customer-facing rows use that policy.

## Results Summary

| Module | Transform | Status |
| --- | --- | --- |
| `rtl/ibex_alu.sv` | `bwlogic_or_from_xor_and` | Formal pass; Yosys 0.66+181 area replay is positive: `5471.4976 -> 5122.4128` chip area, `-6.38%`, and toggle is flat. Max combinational propagation delay regresses `8.83ns -> 10.56ns`, so this is an area/timing tradeoff rather than full-PPA frontier evidence. |
| `rtl/ibex_compressed_decoder.sv` | `rlist_init_formula` | Formal pass; historical Yosys 0.9 replay is positive, but Yosys 0.45 replay regressed. Current customer-facing 0.66 replay is pending independent area/toggle/timing closure. |
| `rtl/ibex_if_stage.sv` | `no_bp_prefetch_direct` | Candidate package only: formal replay closes and selected-toolchain area/timing improve, but final toggle/power convention is pending. See `athanor_artifacts/if_stage_no_bp_prefetch_direct/`. |
| `rtl/ibex_id_stage.sv` | `no_wb_prio_assign` | Candidate package only: formal replay closes and selected-toolchain area/timing improve, but quick internal-VCD toggle smoke regresses `+1.27%`. See `athanor_artifacts/id_stage_no_wb_prio_assign/`. |

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
- selected-toolchain status showing whether the row is customer-facing,
  historical, cross-tool-sensitive, or an area/timing tradeoff

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
- `athanor_artifacts/`
  - Candidate packages for IF-stage and ID-stage parameter-specialization
    transforms. These remain outside the customer-facing frontier until the
    toggle/power convention and promotion bar are settled.

Additional archived receipt rows may appear under `ppa_frontier/` when they
carry complete public manifests, but the top-level README lists the current
customer-facing frontier.
