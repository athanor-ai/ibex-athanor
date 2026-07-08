# ibex_pmp TOR-comparator-share — favorable-tradeoff row (classified)

Selected toolchain `yosys_0_66_181_oss_cad_suite_2026_06_30`, liberty sha ec0e1067.
Classification: `area_tradeoff_yosys66`, status `area_positive_toggle_flat_propagation_delay_negative`
(area -12.51% robust, toggle flat, max propagation delay regression under both objectives).

Receipts here are the classified row (verified by `athanor/verify_public_receipts.py`).
The full cold-replay bundle — sv2v v2001 netlists, `eq.ys` SAT miter, and the toggle
harness (`toggle/tb_toggle.v` + `count_toggle.py`) — lives in
`athanor_artifacts/ibex_pmp_tor_comparator_share/` (see its COMMANDS.md); those
generated replay artifacts are Verible-waived, source RTL `.sv` here stays linted.
