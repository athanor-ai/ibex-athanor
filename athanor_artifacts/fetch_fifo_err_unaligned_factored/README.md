# ibex_fetch_fifo err_unaligned_factored

Discovery packet for the `ibex_fetch_fifo` `err_unaligned` factoring lead.

Status: candidate packet ready for independent replay and lane-owner sanity
read. Do not land as a public accepted row until an independent VM replays
`COMMANDS.md` and the row is reviewed.

Selected lead summary from `lead_manifest.json`:

- Generic cells: 396 -> 395, delta -1 (-0.2525%).
- Liberty-mapped cells: 456 -> 451, delta -5 (-1.0965%).
- Toggle proxy: 4008 -> 4008, delta 0.0%.
- Bounded sequential SAT: k16/k20/k30 all SUCCESS.
- Relation-aware sequential miter: temporal induction SUCCESS.
- Non-vacuity bite: bad `err_unaligned` mutant FAILS in the base case.

The proof packet derives the FIFO occupancy relation from reset/reachability
instead of assuming it externally. The source-level transform is in
`SOURCE_DIFF.patch`.
