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

The table below is the customer-facing summary of the latest Ibex optimization
work in this repository. "Accepted artifact" means the package passes the
current five-part evidence bar for the stated toolchain: area, timing,
toggle/activity, formal equivalence, and replayable hashes. "Candidate" means
some vectors are still missing. "Rejected" means the evidence found a real
regression and the transform should not be promoted as a win. Area is the
primary selected-toolchain metric; mapped-cell count is shown separately because
cell count and liberty-weighted area can move in different directions.

| Module / transform | Status | Area result | Mapped cells | Timing result | Toggle/activity | Formal result | Evidence |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `ibex_multdiv_slow` / `greater_equal_xor_shape` | **Accepted artifact** | 10339.9168 -> 10333.6608, **-0.0605%** | 1351 -> 1361, **+10 cells** | max data arrival 8.13ns -> 7.25ns, **-0.88ns / -10.82%**; WNS/TNS -0.13/-5.66 -> 0/0 | 6117 -> 6117, **0.0%** | 411/411 `$equiv` proven | [`athanor_artifacts/multdiv_slow_greater_equal_xor_shape/`](athanor_artifacts/multdiv_slow_greater_equal_xor_shape/) |
| `ibex_if_stage` / `no_bp_prefetch_direct` | **Candidate: area + timing + formal positive, toggle pending** | 16821.1328 -> 16756.0704, **-0.3868%** | 3396 -> 3403, **+7 cells** | top data arrival 9.2829ns -> 8.9149ns, **-3.9654%**; WNS/TNS 0/0 | pending | 1956/1956 `$equiv` proven | [`athanor_artifacts/if_stage_no_bp_prefetch_direct/`](athanor_artifacts/if_stage_no_bp_prefetch_direct/) |
| `ibex_alu` / `bwlogic_or_from_xor_and` | **Tradeoff: area positive, timing negative** | 5471.4976 -> 5122.4128, **-6.3801%** | 838 -> 788, **50 cells saved / -5.9666%** | max propagation delay 8.83ns -> 10.56ns, **+1.73ns / +19.59%** | 5977 -> 5977, **0.0%** | 1627 cells, 0 unproven | [`athanor/ppa_frontier/ibex_alu_bwlogic/`](athanor/ppa_frontier/ibex_alu_bwlogic/) |
| `ibex_id_stage` / `no_wb_prio_assign` | **Rejected: toggle regression** | 7791.2224 -> 7741.1744, **-0.6424%** | 2268 -> 2188, **80 cells saved / -3.53%** | top data arrival 7.5917ns -> 5.5358ns, **-27.08%**; WNS/TNS 0/0 | 26137 -> 26468, **+1.27%** | 665/665 `$equiv` proven | [`athanor_artifacts/id_stage_no_wb_prio_assign/`](athanor_artifacts/id_stage_no_wb_prio_assign/) |
| `ibex_load_store_unit` / `signext_factor` | **Rejected: toggle regression** | 4695.7536 -> 4664.4736, **-0.6662%** | 1164 -> 1160, **4 cells saved / -0.34%** | max data arrival 5.59ns -> 3.89ns, **-1.70ns / about -30.3%**; WNS/TNS 0/0 | 55424 -> 56421, **+1.79886%** | 287/287 `$equiv` proven | [`athanor_artifacts/load_store_unit_signext_factor/`](athanor_artifacts/load_store_unit_signext_factor/) |

### What This Means

- The strongest current win is `ibex_multdiv_slow`: it improves area and timing,
  keeps toggle flat, and proves equivalence under the selected public replay
  package.
- The IF-stage specialization is promising, but it is not promoted until toggle
  evidence is packaged.
- The ALU row saves area and cells but costs timing; it is useful evidence, not a
  full-PPA customer win.
- The ID-stage and LSU rows are deliberately listed as rejects. They looked good
  on area/timing/formal, but switching activity regressed, so the promotion bar
  correctly stopped them.

## Historical / Cross-Tool Evidence

`ibex_compressed_decoder` / `rlist_init_formula` remains formally proven and was
area-positive under the historical Yosys 0.9 recipe: chip area
4782.0864 -> 4668.2272 (**-2.38095%**), mapped cells 810 -> 774
(**36 cells saved / -4.44%**), RTL/VCD toggle flat at 800 -> 800, and OpenSTA
10ns timing met with max data arrival 3.00ns -> 2.55ns. It is not listed as a
current selected-toolchain customer frontier row because later replays showed
cross-tool sensitivity; selected Yosys 0.66+181 packaging is required before
promotion.

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
