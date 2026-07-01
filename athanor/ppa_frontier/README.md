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

The selected customer-facing replay policy is
[`toolchain_policy.json`](toolchain_policy.json): OSS CAD Suite 2026-06-30 /
Yosys 0.66+181, the recorded Sky130 liberty hash, and the recorded ABC mapping
recipe. Public customer-facing rows must reference that policy from their
`manifest.json` and must preserve selected-toolchain receipts. Standalone
combinational timing evidence uses max input-to-output propagation delay;
unconstrained OpenSTA output is not customer-facing timing evidence.

Run the manifest gate before changing this directory:

```bash
python3 athanor/ppa_frontier/verify_toolchain_manifest.py
```

Rows with synthesis-flow sensitivity must pin the exact accepted toolchain and
record divergent toolchain results in their public receipts. They are not
portable synthesis-flow claims.
