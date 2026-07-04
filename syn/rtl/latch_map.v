// Copyright lowRISC contributors.
// Licensed under the Apache License, Version 2.0, see LICENSE for details.
// SPDX-License-Identifier: Apache-2.0

// Map latch primitives to a specific cell
module $_DLATCH_P_ (input E, input D, output Q);
  sky130_fd_sc_hd__dlxtp_1 _TECHMAP_REPLACE_ (
    .GATE(E),
    .D(D),
    .Q(Q)
  );
endmodule

module $_DLATCH_N_ (input E, input D, output Q);
  sky130_fd_sc_hd__dlxtn_1 _TECHMAP_REPLACE_ (
    .GATE_N(E),
    .D(D),
    .Q(Q)
  );
endmodule
