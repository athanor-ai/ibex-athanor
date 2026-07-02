# ibex_load_store_unit sign-extension factoring candidate

Classification: rejected_toggle_regression, not accepted.

Candidate shape: factor repeated load sign-extension mux arms from `if (!data_sign_ext_q) zero_extend else sign_extend` into `{N{data_sign_ext_q & sign_bit}}` concatenations for `rdata_h_ext` and `rdata_b_ext`.

Local scratch receipt under selected toolchain:
- Yosys 0.66+181 + sky130 area: 4695.7536 -> 4664.4736 (-0.6662%).
- OpenSTA 10ns clock / 2ns IO: max data arrival 5.59ns -> 3.89ns; WNS/TNS remain 0.00/0.00.
- Yosys whole-module equivalence: 287/287 cells proven with `equiv_simple -seq 5` + `equiv_induct -seq 32`.
- Toggle/power: measured with deterministic LSU-local iverilog/VCD replay:
  55424 -> 56421 toggles (+1.79886%), a regression.

Boundary: this is a local candidate package for independent cold replay. It is not a customer claim and not an accepted ibex optimization. The area/timing/formal evidence reproduced, but the toggle gate fails.
