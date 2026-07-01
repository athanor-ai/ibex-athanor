# Athanor Ibex Candidate Artifacts

This directory contains auditable candidate packages that are ahead of the
customer-facing `athanor/ppa_frontier/` rows.

Each package pins:

- gold and gate Verilog artifacts
- selected Yosys 0.66/OpenSTA replay logs
- formal equivalence scripts/logs when available
- timing constraints and SHA-256 manifests
- any early toggle or switching smoke receipts

These packages are engineering evidence, not customer frontier claims. Promotion
to `athanor/ppa_frontier/` requires the selected public toolchain policy,
formal replay, area replay, timing replay, and the agreed toggle/power
convention to be complete and independently reviewed.

## Packages

| Package | Status |
| --- | --- |
| [`if_stage_no_bp_prefetch_direct/`](if_stage_no_bp_prefetch_direct/) | Formal replay and area/timing replay are positive under Yosys 0.66. Toggle convention is pending. |
| [`id_stage_no_wb_prio_assign/`](id_stage_no_wb_prio_assign/) | Formal replay and area/timing replay are positive under Yosys 0.66. Quick internal-VCD toggle smoke regresses +1.27%, so final power/toggle convention is pending. |
