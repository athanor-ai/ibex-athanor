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
| [`multdiv_slow_greater_equal_xor_shape/`](multdiv_slow_greater_equal_xor_shape/) | Accepted selected-toolchain artifact: area -0.0605%, max data arrival -0.88ns / -10.82%, toggle flat, formal 411/411. |
| [`multdiv_fast_greater_equal_xor_shape/`](multdiv_fast_greater_equal_xor_shape/) | Accepted artifact: cell count flat, max propagation delay -0.28ns / -2.58%, toggle flat, formal 772/772. |
| [`if_stage_expanded_predicate_factor/`](if_stage_expanded_predicate_factor/) | Candidate: top-level area -0.02885%, whole-core WNS improves on all recorded groups, formal 1956/1956, corrected pinned toggle convention flat. |
| [`if_stage_no_bp_prefetch_direct/`](if_stage_no_bp_prefetch_direct/) | Candidate: formal replay and area/timing replay are positive under Yosys 0.66, corrected pinned toggle convention flat. |
| [`id_stage_no_wb_prio_assign/`](id_stage_no_wb_prio_assign/) | Rejected for promotion: area/timing/formal are positive, but quick internal-VCD toggle smoke regresses +1.27%. |
| [`load_store_unit_signext_factor/`](load_store_unit_signext_factor/) | Rejected for promotion: area/timing/formal are positive, but deterministic LSU-local toggle replay regresses +1.79886%. |
