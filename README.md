# Athanor Optimized Ibex

Athanor AI applies formally checked RTL transformations to production hardware
designs and records the PPA evidence needed to audit each result. This fork
starts from the industry-standard lowRISC Ibex RISC-V core and adds optimized
RTL plus public proof and measurement receipts. Results are pinned to the
recorded open-source toolchain and should be read as reproducible
toolchain-specific evidence.

## Verified PPA Frontier

| Module | Optimized RTL | Cells before -> after | Delta | Toggle | Timing | Proof certificates |
| --- | --- | ---: | ---: | --- | --- | --- |
| `ibex_alu` | [`rtl/ibex_alu.sv`](rtl/ibex_alu.sv) | 842 -> 785 mapped cells | -6.77% | 5977 -> 5977, 0.0% | WNS -4.29 ns -> -3.75 ns | [formal](athanor/ppa_frontier/ibex_alu_bwlogic/formal_cert.json), [Lean](athanor/ppa_frontier/ibex_alu_bwlogic/lean_receipt.json), [manifest](athanor/ppa_frontier/ibex_alu_bwlogic/manifest.json) |
| `ibex_compressed_decoder` | [`athanor/ppa_frontier/ibex_compressed_decoder_rlist/artifacts/ibex_compressed_decoder_rlist_init_formula.sv`](athanor/ppa_frontier/ibex_compressed_decoder_rlist/artifacts/ibex_compressed_decoder_rlist_init_formula.sv) | 810 -> 774 mapped cells | -4.44% mapped cells; -2.38% chip area | 800 -> 800, 0.0%; independent replay 3423 -> 3423 | WNS/TNS 0.00/0.00 -> 0.00/0.00; independent replay +0.13 ns slack | [formal](athanor/ppa_frontier/ibex_compressed_decoder_rlist/formal_cert.json), [Lean](athanor/ppa_frontier/ibex_compressed_decoder_rlist/lean_receipt.json), [manifest](athanor/ppa_frontier/ibex_compressed_decoder_rlist/manifest.json) |

## Receipt Layout

- Public frontier receipts: [`athanor/ppa_frontier/`](athanor/ppa_frontier/)
- Area receipts: `area.json`
- Toggle/activity receipts: `power.json`
- Timing receipts: `timing.json`
- Formal equivalence receipts: `formal_cert.json`
- Machine-checked helper proofs: `lean_receipt.json` and the linked Lean files

The compressed-decoder result is cross-tool sensitive: it is positive under the
recorded Yosys 0.9 recipe and regresses under one Yosys 0.45 replay. The
receipt records this explicitly; the claim is pinned-toolchain evidence, not a
portable assertion across every synthesis flow.

## Upstream Ibex

The original lowRISC documentation, examples, and source tree are preserved in
this repository. Start with [`doc/`](doc/) for the upstream Ibex manual and
[`LICENSE`](LICENSE) for license terms.
