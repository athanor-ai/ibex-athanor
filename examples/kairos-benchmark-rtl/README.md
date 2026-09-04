# Kairos benchmark RTL

The RTL fixtures the Kairos verification benchmark runs against, checked in so the
results can be reproduced and the tickets that cite them stay readable.

Until now this set lived only on one bench host, in seven copies, under
`~/kairos-bench/<run>/fixtures/`. Every ticket in the Linear project **Benchmark
Findings** (ATH-4016 … ATH-4047) cites evidence produced from these files.

33 files, ~1,700 lines, 168 KB. Copied byte-for-byte from
`~/kairos-bench/main-run-2026-08-28-e0eb51f/fixtures/`.

## Provenance

### Ibex — `ibex_rf_*.sv`

`ibex_rf_gold.sv` is **byte-identical** to `rtl/ibex_register_file_fpga.sv` in this
repository (sha256 `85fc2800b2c3f62f8d668bc5…`), unmodified, license header intact:

```
// Copyright lowRISC contributors.
// Copyright 2018 ETH Zurich and University of Bologna, see also CREDITS.md.
// SPDX-License-Identifier: Apache-2.0
```

The rest are derived from it:

| file | relationship |
| --- | --- |
| `ibex_rf_gold.sv` | upstream `rtl/ibex_register_file_fpga.sv`, unmodified |
| `ibex_rf_cand.sv` | equivalent variant — equivalence should prove |
| `ibex_rf_mutant.sv` | deliberate defect — equivalence should refute |
| `ibex_rf_true_prop.sv` | gold plus an SVA assertion that holds |
| `ibex_rf_false_prop.sv` | gold plus an SVA assertion that fails |
| `ibex_rf_*_prop_nolabel.sv` | the same two with the block labels stripped |

The `_nolabel` pairs differ from their originals by **two lines only** — the
`begin : sync_write` / `end : sync_write` labels at lines 59 and 63. They exist
because the pinned EBMC rejects the trailing `end : name`, so the labelled file
fails to parse while the stripped one verifies. That pair is the evidence behind
**ATH-4022**; the labels are upstream Ibex's, not something added here.

### OpenC910 — `c910_*.v`

From T-Head's OpenC910, license header intact:

```
/*Copyright 2019-2021 T-Head Semiconductor Co., Ltd.
Licensed under the Apache License, Version 2.0
```

`c910_icg_*.v` is the `gated_clk_cell` integrated clock gate; `c910_icache_*.v` is
an icache slice (347 lines, the largest fixture here). `c910_icg_mutant.v` is the
case behind the Lean-lane counts in **ATH-4019**.

*Not yet pinned to an upstream revision.* The files came from OpenC910 but the
harness notes did not record which commit, and `athanor-ai/openc910-athanor` did
not return a match on the module name. Worth confirming before anyone treats these
as a faithful snapshot.

### Written for the harness — everything else

`crc8_*`, `mult12_*`, `minmem_*`, `seqflop_*`, `seqmin_*`, `seqrst_*`, `sequni_*`,
`gold.v`/`candidate.v`, `c910_sram_stubs.v`, `lean_property.sv`.

No copyright headers; the benchmark notes state the harness "was built from
scratch". Mostly 3–15 line gold/candidate pairs that exercise engine dispatch and
lane selection rather than solver scale. `c910_sram_stubs.v` is a stub supplying
the SRAM macros the icache instantiates.

## What this set is and is not

It exercises **engine dispatch, lane selection and refusal paths** — which is where
every Benchmark Findings ticket landed. The largest design is a 347-line icache and
the Ibex register file is 83 lines, so it says nothing about solver scaling or
behaviour on production-sized designs. The harness notes flag the same limitation.

## Licensing

Ibex files are Apache-2.0 (lowRISC / ETH Zurich and University of Bologna). OpenC910
files are Apache-2.0 (T-Head Semiconductor). Both are redistributable and every
header is preserved verbatim. Note the OpenC910 files carry a different copyright
holder from the rest of this repository.
