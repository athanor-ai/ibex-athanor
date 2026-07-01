# Athanor Optimized Ibex

Athanor AI applies formally checked RTL transformations to production hardware
designs and records the PPA evidence needed to audit each result. This fork
starts from the industry-standard lowRISC Ibex RISC-V core and adds optimized
RTL plus public proof and measurement receipts. Results are pinned to the
recorded open-source toolchain and should be read as reproducible evidence for
the stated toolchain. The current customer-facing area baseline is OSS CAD
Suite 2026-06-30 / Yosys 0.66+181 with the Sky130 liberty and ABC mapping
recipe recorded in the receipts. Public manifests are checked by
[`athanor/verify_public_receipts.py`](athanor/verify_public_receipts.py) so
future receipt updates must preserve the selected-toolchain policy.

## Current Toolchain Rebaseline

| Module | Optimized RTL | Yosys 0.66+181 area | Delta | Toggle | Timing | Proof certificates |
| --- | --- | ---: | ---: | --- | --- | --- |
| `ibex_alu` | [`rtl/ibex_alu.sv`](rtl/ibex_alu.sv) | 5471.4976 -> 5122.4128 chip area; 838 -> 788 mapped cells | -6.38% chip area | 5977 -> 5977, flat | Timing tradeoff: max propagation delay 8.83ns -> 10.56ns | [area](athanor/ppa_frontier/ibex_alu_bwlogic/area_yosys66.json), [toggle/timing](athanor/ppa_frontier/ibex_alu_bwlogic/toggle_timing_yosys66.json), [formal](athanor/ppa_frontier/ibex_alu_bwlogic/formal_cert.json), [Lean](athanor/ppa_frontier/ibex_alu_bwlogic/lean_receipt.json), [manifest](athanor/ppa_frontier/ibex_alu_bwlogic/manifest.json) |

The ALU row is area-positive and formally proven, but it is not a full-PPA
frontier row under the current Yosys 0.66+181/OpenSTA replay because max
combinational propagation delay regresses. It remains useful area-optimization
evidence and an explicit area/timing tradeoff for customers to evaluate against
their clock budget.

## Current Candidate Artifacts

The following parameter-specialization candidates are pushed as auditable
artifact packages. They are not promoted into `athanor/ppa_frontier/` until the
toggle/power convention and final customer promotion bar are settled.

| Module | Transform | Area | Timing | Formal | Toggle status | Artifacts |
| --- | --- | ---: | ---: | --- | --- | --- |
| `ibex_if_stage` | specialize default `BranchPredictor=0` prefetch branch path | 16821.1328 -> 16756.0704, -0.3868% | top data arrival 9.2829ns -> 8.9149ns, -3.9654%; WNS/TNS met | Yosys 0.66 replay: 1956/1956 `$equiv` cells proven | final toggle/power convention pending | [`athanor_artifacts/if_stage_no_bp_prefetch_direct/`](athanor_artifacts/if_stage_no_bp_prefetch_direct/) |
| `ibex_id_stage` | specialize default `WritebackStage=0` controller exception priority | 7791.2224 -> 7741.1744, -0.6424% | top data arrival 7.5917ns -> 5.5358ns, -27.08%; WNS/TNS met | Yosys 0.66 replay included in package | quick internal-VCD smoke +1.27%; realistic/convention replay pending | [`athanor_artifacts/id_stage_no_wb_prio_assign/`](athanor_artifacts/id_stage_no_wb_prio_assign/) |

## Rebaseline Pending Promotion

`ibex_compressed_decoder` / `rlist_init_formula` remains formally proven and
was area-positive under the historical Yosys 0.9 recipe, but it is
cross-tool-sensitive. Selected-toolchain replay evidence is under review, but
the row is not listed as a current customer-facing frontier row until the Yosys
0.66+181 receipts are packaged, independently reviewed, and promoted under the
same public manifest policy used for the ALU row.

## Receipt Layout

- Public frontier receipts: [`athanor/ppa_frontier/`](athanor/ppa_frontier/)
- Candidate artifact packages:
  [`athanor_artifacts/`](athanor_artifacts/)
- Selected toolchain policy:
  [`athanor/toolchain_policy.json`](athanor/toolchain_policy.json)
- Public manifest verifier:
  `python3 athanor/verify_public_receipts.py`
- Area receipts: `area.json`
- Toggle/activity receipts: `power.json`
- Timing receipts: `timing.json`
- Formal equivalence receipts: `formal_cert.json`
- Machine-checked helper proofs: `lean_receipt.json` and the linked Lean files

Historical Yosys 0.9 receipts remain available under
[`athanor/ppa_frontier/`](athanor/ppa_frontier/) for auditability. They are
cross-tool sensitivity evidence, not a substitute for the selected
customer-facing Yosys 0.66+181 baseline.

## Upstream Ibex

The original lowRISC documentation, examples, and source tree are preserved in
this repository. Start with [`doc/`](doc/) for the upstream Ibex manual and
[`LICENSE`](LICENSE) for license terms.
