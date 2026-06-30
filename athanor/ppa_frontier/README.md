# PPA Frontier Receipts

This directory stores replay artifacts for optimized Ibex modules.

Each module directory should include:

- optimized gate RTL
- original/gold RTL when available
- formal receipt
- area, power/toggle, and timing receipts
- Lean or other proof receipts when available
- replay summary and manifest with artifact hashes

Only rows that pass the current verification bar should be added here.
PPA-positive filters with incomplete formal proof belong in the research
ledger, not in this frontier branch.
