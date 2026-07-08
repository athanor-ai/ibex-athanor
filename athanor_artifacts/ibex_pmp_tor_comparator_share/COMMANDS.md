# ibex_pmp TOR-comparator-share — favorable-tradeoff row, cross-VM replay

Selected toolchain: `yosys_0_66_181_oss_cad_suite_2026_06_30`
(`/workdir/_tools/oss-cad-suite-20260630/bin/yosys`), liberty
`sky130_fd_sc_hd__tt_025C_1v80.lib` (sha256 ec0e1067…).

Transform: in TOR mode `region_start_addr[r] == csr_pmp_addr_i[r-1]`, and
`region_match_gt` is consumed only in the TOR branch, so `gt[r]` is rewired to
compare against that boundary (r==0 -> |addr) — sharing one magnitude comparator
per boundary with `lt[r-1]`. Synthesis cannot find it (mode-dependent mux).

## Formal equivalence (authority; toolchain-independent)
    yosys -q eq.ys     # combinational SAT miter gold vs gate: "no model found: SUCCESS"
Non-vacuity: a seeded-inequivalent mutant must produce a model.

## Area (selected y0.66)
    yosys -p "read_verilog ibex_pmp_gold_v2001.v; hierarchy -check -top ibex_pmp; \
      proc; flatten; synth -top ibex_pmp; dfflibmap -liberty <lib>; abc -liberty <lib>; stat -liberty <lib>"
    # gold 13042.5088 ; gate (…share_v2001.v) 11410.944 => -12.51%

## Timing (combinational max propagation delay; the load-bearing metric)
    # OpenSTA report_checks -path_delay max over the y0.66+abc mapped netlists,
    # loose 10ns virtual clock, zero I/O delay:
    # gold 5.467 ns ; gate 5.515 ns => +0.9% REGRESSION (area-oriented).
    # objective band: -fast makes it +18% (also worse) => robust regression.

## Toggle (iverilog boundary, sv2v-normalized, 200 vectors)
    # gold 2664 == gate 2664 => 0.0% FLAT.

## Classification
area -12.51% (robust) + toggle flat + propagation-delay regression =
row_contract `area_tradeoff_yosys66`, status
`area_positive_toggle_flat_propagation_delay_negative`. FAVORABLE TRADEOFF, not a win.

## Verify
    python3 athanor/verify_public_receipts.py   # must be green

## Toggle cold-replay (closes Ronald cross-VM note — reproduce the exact 2664)
    iverilog -g2012 -D VCDF='"tog_gold.vcd"' -o tog_gold.vvp toggle/tb_toggle.v ibex_pmp_gold_v2001.v && vvp tog_gold.vvp
    iverilog -g2012 -D VCDF='"tog_gate.vcd"' -o tog_gate.vvp toggle/tb_toggle.v ibex_pmp_tor_comparator_share_v2001.v && vvp tog_gate.vvp
    python3 toggle/count_toggle.py tog_gold.vcd   # 2664
    python3 toggle/count_toggle.py tog_gate.vcd   # 2664  => flat
