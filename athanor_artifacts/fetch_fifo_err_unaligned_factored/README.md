# ibex_fetch_fifo err_unaligned_factored

Discovery packet for the `ibex_fetch_fifo` `err_unaligned` factoring lead.

Status: draft candidate packet with independent replay requested. Do not land
as a public accepted row until independent replay and ibex-lane review both
stamp the corrected packet.

Current packet summary:

- Generic cells: 396 -> 395, delta -1 (-0.2525%).
- Liberty-mapped cells: 456 -> 451, delta -5 (-1.0965%).
- Primary replay toggle metric: SAIF transition-count sum 34031 -> 34031,
  delta 0.0%.
- Historical lead-probe toggle counter: 4008 -> 4008, delta 0.0%. This is
  preserved in `lead_manifest.json` for continuity with the discovery probe;
  `replay_toggle.py` reports the SAIF transition-count sum as the public replay
  metric.
- Bounded sequential SAT: k16/k20/k30 all SUCCESS.
- Relation-aware sequential miter: temporal induction SUCCESS.
- No-external-occupancy miter: temporal induction SUCCESS, so the occupancy
  relation is derived from reset/reachability rather than externally assumed.
- Non-vacuity bite: bad `err_unaligned` mutant FAILS in the base case.

The proof packet derives the FIFO occupancy relation from reset/reachability
instead of assuming it externally. The source-level transform is in
`SOURCE_DIFF.patch`. The old canonical `equiv_simple + equiv_induct` result
that left 1/454 cells unproven is retained as prior evidence only; it is not
the active packet classification after the relation-aware miter closure.
