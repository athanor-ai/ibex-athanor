# PPA Frontier Receipts

This directory stores replay artifacts for optimized Ibex modules.

Each module directory should include:

- optimized gate RTL
- original/gold RTL when available
- formal receipt
- area, power/toggle, and timing receipts
- Lean or other proof receipts when available
- manifest with artifact hashes

Only rows that pass the current verification bar should be added here.
PPA-positive filters with incomplete formal proof belong in the research
ledger, not in this frontier branch.

Rows with synthesis-flow sensitivity must pin the exact recorded toolchain and
record divergent toolchain results in their public receipts. They are not
portable synthesis-flow claims. While the selected-toolchain rebaseline is in
progress, PPA rows in this directory should be described as hash-backed
toolchain evidence rather than final flow-general frontier claims.
