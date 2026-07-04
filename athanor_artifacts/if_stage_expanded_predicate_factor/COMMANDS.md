# Replay Commands

All commands below assume a clean checkout of `athanor-ai/ibex-athanor` at the
package `base_commit` recorded in `top_level_ppa_yosys66.json`.

## Verify Package Hashes

```bash
sha256sum -c athanor_artifacts/if_stage_expanded_predicate_factor/SHA256SUMS
```

## Rebuild the Source Edit

`SOURCE_DIFF.patch` applies directly to `rtl/ibex_if_stage.sv` and preserves the
module name `ibex_if_stage`.

```bash
git apply athanor_artifacts/if_stage_expanded_predicate_factor/SOURCE_DIFF.patch
```

If a side-by-side local harness renames the candidate module with a `_gate`
suffix, rename it back to `ibex_if_stage` before whole-core synthesis. The
top-level `ibex_top` flow instantiates `ibex_if_stage`.

## Rebuild Gold and Gate Verilog Artifacts

Use the same sv2v pin recorded in `top_level_ppa_yosys66.json`.

```bash
export SV2V=/workdir/.local/bin/sv2v

$SV2V -D SYNTHESIS \
  -I vendor/lowrisc_ip/ip/prim/rtl \
  -I vendor/lowrisc_ip/dv/sv/dv_utils \
  rtl/ibex_pkg.sv \
  rtl/ibex_fetch_fifo.sv \
  rtl/ibex_prefetch_buffer.sv \
  rtl/ibex_compressed_decoder.sv \
  rtl/ibex_if_stage.sv \
  > /tmp/if_stage_gold.v

git apply athanor_artifacts/if_stage_expanded_predicate_factor/SOURCE_DIFF.patch

$SV2V -D SYNTHESIS \
  -I vendor/lowrisc_ip/ip/prim/rtl \
  -I vendor/lowrisc_ip/dv/sv/dv_utils \
  rtl/ibex_pkg.sv \
  rtl/ibex_fetch_fifo.sv \
  rtl/ibex_prefetch_buffer.sv \
  rtl/ibex_compressed_decoder.sv \
  rtl/ibex_if_stage.sv \
  > /tmp/if_stage_gate.v
```

The packaged artifact hashes are:

```text
ec84d9b70656cefe286c06a7dcb57f9a7bdb7a414134fd62f74b563316c5a2c9  gold.v
33ccfff935e6f9bf9ced0b4b0c446ef879b71817efd9f31dc39dcdfe674f897b  gate_expanded_predicate_factor.v
```

## Replay Formal Equivalence

```bash
cd athanor_artifacts/if_stage_expanded_predicate_factor
/workdir/_tools/oss-cad-suite-20260630/bin/yosys -s equiv_yosys66.ys
```

Expected result:

```text
Found 1956 $equiv cells in equiv:
  Of those cells 1956 are proven and 0 are unproven.
Equivalence successfully proven!
```

## Replay Top-Level PPA

Run the baseline from a clean checkout, then apply `SOURCE_DIFF.patch` and run
the gate.

```bash
export PATH=/workdir/_tools/oss-cad-suite-20260630/bin:/workdir/.local/bin:/usr/local/bin:$PATH
export LR_SYNTH_CELL_LIBRARY_PATH=/workdir/.main-6b922e97/src/kairos/data/liberty/sky130_fd_sc_hd__tt_025C_1v80.lib
export LR_SYNTH_CELL_LIBRARY_NAME=nangate

cd syn
./syn_yosys.sh syn_out/baseline_if_expanded_factor_replay

cd ..
git apply athanor_artifacts/if_stage_expanded_predicate_factor/SOURCE_DIFF.patch

cd syn
./syn_yosys.sh syn_out/gate_if_expanded_factor_replay
```

The package was produced with the same flow and records:

```text
area: 108428.9920 -> 108397.7120 (-0.02885%)
overall WNS: -484.8247 ns -> -470.9621 ns (+13.8626 ns)
reg2reg WNS: -484.8247 ns -> -470.9621 ns (+13.8626 ns)
reg2out WNS: -436.0064 ns -> -422.2023 ns (+13.8041 ns)
in2reg WNS: -249.6181 ns -> -249.4600 ns (+0.1581 ns)
in2out WNS: -200.6972 ns -> -200.5294 ns (+0.1678 ns)
```

## Replay Pinned Toggle Convention

The package includes a pinned `kairos.ibex.toggle.control_path.v1` replay. Run
the same harness against the packaged gold and gate artifacts:

```bash
python3 athanor/toggle_convention/harness.py \
  --gold athanor_artifacts/if_stage_expanded_predicate_factor/gold.v \
  --gate athanor_artifacts/if_stage_expanded_predicate_factor/gate_expanded_predicate_factor.v \
  --top ibex_if_stage \
  --out-dir athanor_artifacts/if_stage_expanded_predicate_factor/logs/convention_v1
```

Expected result:

```text
gold_toggles: 306184
gate_toggles: 311729
toggle_delta_pct: +1.811003
toggle_status: regression
```

## Boundary

This is rejected scout evidence. The source patch is bounded, formal equivalence
closes, and top-level area/timing improve, but the pinned toggle convention
regresses. Do not promote it as an accepted Ibex optimization unless a future,
independently reviewed variant closes the full bar without weakening the toggle
convention.
