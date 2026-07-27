# ibex_pmp tor_boundary_comparator_share

Cold-replay bundle for the `ibex_pmp` TOR-boundary comparator-share transform
(`transform_class: tor_boundary_comparator_share`). The classified receipt row
lives in `athanor/ppa_frontier/ibex_pmp_tor_comparator_share/` (schema
`public_frontier_manifest_v1`); this directory holds the replay scripts. Every
claim below restates that manifest and its receipt files; nothing here goes
beyond what they state.

Status (verbatim from the manifest):
`formal_pass_yosys66_area_positive_toggle_flat_propagation_delay_negative`,
row contract `area_tradeoff_yosys66`. Per the manifest's own tradeoff note:
area improves -12.51% and toggle is flat under the selected toolchain, but max
input-to-output propagation delay regresses +0.9% (area-oriented; worse under
`-fast`). Favorable area/timing tradeoff, not a full-PPA frontier row.

What holds, per receipt file:

- Formal equivalence (`formal_cert.json`): yosys SAT miter over the sv2v v2001
  two-file netlists, all inputs plus trigger imported over `pmp_req_err_o`,
  "no model found" SUCCESS, non-vacuous (a seeded mutant on `pmp_req_err_o`
  FAILS). Scope limit stated by the certificate itself: this is a
  single-instrument result and `independent_verification.status` is
  `pending_cross_vm` — independent cross-VM replay of the comb-EC bites and
  the area/toggle/propagation-delay numbers is required before acceptance.
- Area (`area_yosys66.json`, the manifest-selected area receipt): Liberty
  chip area 13042.5088 -> 11410.944 (-12.51%) and ABC-mapped Sky130 cells
  2141 -> 1933 (-9.7151%) under Yosys 0.66+181 / OSS CAD Suite 2026-06-30,
  liberty sha ec0e1067. The two numbers are different conventions of the same
  receipt (stat Liberty area vs mapped-cell histogram); its own metric note
  adds that full-PPA customer-facing use is blocked by the propagation-delay
  regression below. `independent_replay_required` is true.
- Timing (`toggle_timing_yosys66.json`, the manifest-selected timing receipt,
  convention `combinational_max_propagation_delay`): OpenSTA max propagation
  delay 5.467 ns -> 5.515 ns (+0.878%), status `regression`. The 10 ns
  virtual-clock check itself is met (WNS/TNS 0.0); the regression is the
  max-delay convention the manifest classifies this row under.
- Toggle (`power.json` / `toggle_timing_yosys66.json`): iverilog toggle on
  sv2v-normalized RTL, 2664 -> 2664, delta 0.0% (flat), 200 sim cycles.

What is not covered: the manifest states no scope beyond the module-level
rows above. It makes no whole-core `ibex_top`, ISA, signoff, or
customer-design claim, and any scope not stated in the manifest is unstated
rather than implied. `full_ppa_frontier` is false.

How to replay: see `COMMANDS.md` in this directory. Step 0 regenerates the
sv2v v2001 netlists (hashes pinned in `area_yosys66.json`); `eq.ys` is the
formal-equivalence authority; the area/timing/toggle recipes reproduce the
numbers above. The receipt row is checked by
`athanor/verify_public_receipts.py`. Generated replay artifacts are not
committed (regenerable; kept out of the Verible lint scope).
