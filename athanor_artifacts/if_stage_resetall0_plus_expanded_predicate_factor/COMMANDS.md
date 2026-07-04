# Replay Commands

All commands below assume a clean checkout of `athanor-ai/ibex-athanor` at the
package `base_commit` recorded in `top_level_first_receipt.json`.

## Verify Package Hashes

```bash
sha256sum -c athanor_artifacts/if_stage_resetall0_plus_expanded_predicate_factor/SHA256SUMS
```

## Rebuild the Source Edit

`SOURCE_DIFF.patch` applies directly to `rtl/ibex_if_stage.sv` and preserves the
module name `ibex_if_stage`.

```bash
git apply athanor_artifacts/if_stage_resetall0_plus_expanded_predicate_factor/SOURCE_DIFF.patch
```

If a side-by-side local harness renames the candidate module with a `_gate`
suffix, rename it back to `ibex_if_stage` before whole-core synthesis. The
top-level `ibex_top` flow instantiates `ibex_if_stage`.

## Replay Via Top-Level-First Harness

```bash
python3 athanor/top_level_first.py \
  --patch athanor_artifacts/if_stage_resetall0_plus_expanded_predicate_factor/SOURCE_DIFF.patch \
  --core athanor/configs/ibex_top_yosys66.json \
  --candidate-name if_stage_resetall0_plus_expanded_predicate_factor_replay \
  --unit ibex_if_stage \
  --out /tmp/if_stage_resetall0_plus_expanded_predicate_factor_replay \
  --force-fresh
```

Expected local classification before independent cold replay:

```text
FIVE-POINT POSITIVE
```

Expected key values:

```text
area: 108428.9920 -> 108397.7120 (-0.02885%)
overall WNS: -484.8247 ns -> -470.9621 ns (+13.8626 ns)
reg2reg WNS: -484.8247 ns -> -470.9621 ns (+13.8626 ns)
reg2out WNS: -436.0064 ns -> -422.2023 ns (+13.8041 ns)
in2reg WNS: -249.6181 ns -> -249.4600 ns (+0.1581 ns)
in2out WNS: -200.6972 ns -> -200.5294 ns (+0.1678 ns)
formal: 1956/1956 proven
toggle: 311729 -> 311729 (0.0%)
```

## Boundary

This package is candidate evidence only. It is not an accepted win until the
independent cold replay reproduces the source patch, top-level PPA, formal
equivalence, and toggle receipt.
