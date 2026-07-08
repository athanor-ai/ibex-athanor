# ibex_pmp TOR-comparator-share — cold-replay bundle

The classified row (receipts, verify_public_receipts) is in
`athanor/ppa_frontier/ibex_pmp_tor_comparator_share/`. This bundle holds the
cold-replay scripts. The sv2v-generated v2001 netlists + yosys area logs are NOT
committed (regenerable + kept out of the Verible lint scope); regenerate them here:

## Step 0 — regenerate the v2001 netlists (deterministic; hashes pinned in the row's area_yosys66.json)
    R=../../athanor/ppa_frontier/ibex_pmp_tor_comparator_share/artifacts
    sv2v -I <ibex prim incdir> $R/ibex_pkg.sv $R/ibex_pmp.sv                       --write=ibex_pmp_gold_v2001.v
    sv2v -I <ibex prim incdir> $R/ibex_pkg.sv $R/ibex_pmp_tor_comparator_share.sv  --write=ibex_pmp_tor_comparator_share_v2001.v

## Formal equivalence (authority): yosys eq.ys => "no model found: SUCCESS" (12480 vars); non-vacuous (seed a mutant on pmp_req_err_o -> FAIL)
## Area (y0.66): read_verilog *_v2001.v; hierarchy -check -top ibex_pmp; proc; flatten; synth -top ibex_pmp; dfflibmap -liberty <lib>; abc -liberty <lib>; stat  => gold 13042.5088, gate 11410.944 (-12.51%)
## Timing: OpenSTA max propagation delay over y0.66+abc mapped netlists, 10ns virtual clock => gold 5.467, gate 5.515 (+0.9% area-oriented; +18% -fast) = robust regression
## Toggle (flat): iverilog -g2012 toggle/tb_toggle.v <v2001> -> vvp -> count_toggle.py => gold 2664 == gate 2664
