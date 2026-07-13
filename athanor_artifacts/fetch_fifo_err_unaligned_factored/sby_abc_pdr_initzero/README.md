# Relation-Aware SBY/ABC PDR Receipt

This nested packet adds the second sequential proof leg for the
`ibex_fetch_fifo` `err_unaligned_factored` candidate.

Scope:

- Module: `ibex_fetch_fifo`
- Candidate: `err_unaligned_factored_risky`
- Engine: SymbiYosys with ABC PDR
- Top: `ibex_fetch_fifo_relation_seq_no_occupancy_miter_initzero`
- State relation: equality of the exposed FIFO state vectors
  `valid_q`, `err_q`, `rdata_q`, and `instr_addr_q`
- Initial relation: both exposed FIFO states are constrained to zero at the
  initial step
- Observable relation: equality of `busy_o`, `out_valid_o`, `out_addr_o`,
  `out_rdata_o`, `out_err_o`, and `out_err_plus2_o`

This is proof evidence for the module-local candidate under the stated
init-zero/state-relation scope. It is not a whole-core claim and not a
customer-ready RTL integration claim.

The replay uses the parent packet's hash-pinned files:

- `../ibex_fetch_fifo_gold_exposed.v`
- `../ibex_fetch_fifo_gate_exposed.v`
- `../ibex_fetch_fifo_gate_mutant_exposed.v`

The positive case must prove with ABC PDR. The mutant case replaces the gate
file with `ibex_fetch_fifo_gate_mutant_exposed.v` and must fail, preserving the
non-vacuity bite.
