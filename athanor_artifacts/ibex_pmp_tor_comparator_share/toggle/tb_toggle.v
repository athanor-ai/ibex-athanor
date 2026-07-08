`timescale 1ns/1ps
module tb_toggle;
  reg  [23:0]  csr_pmp_cfg_i;
  reg  [135:0] csr_pmp_addr_i;
  reg  [2:0]   csr_pmp_mseccfg_i;
  reg          debug_mode_i;
  reg  [3:0]   priv_mode_i;
  reg  [67:0]  pmp_req_addr_i;
  reg  [3:0]   pmp_req_type_i;
  wire [0:1]   pmp_req_err_o;
  integer i;
  ibex_pmp dut(.csr_pmp_cfg_i(csr_pmp_cfg_i), .csr_pmp_addr_i(csr_pmp_addr_i),
    .csr_pmp_mseccfg_i(csr_pmp_mseccfg_i), .debug_mode_i(debug_mode_i),
    .priv_mode_i(priv_mode_i), .pmp_req_addr_i(pmp_req_addr_i),
    .pmp_req_type_i(pmp_req_type_i), .pmp_req_err_o(pmp_req_err_o));
  initial begin
    $dumpfile(`VCDF);
    $dumpvars(0, tb_toggle);
    csr_pmp_cfg_i=0; csr_pmp_addr_i=0; csr_pmp_mseccfg_i=0; debug_mode_i=0;
    priv_mode_i=0; pmp_req_addr_i=0; pmp_req_type_i=0; #2;
    for (i=0;i<200;i=i+1) begin
      csr_pmp_cfg_i   = {$random};
      csr_pmp_addr_i  = {$random,$random,$random,$random,$random};
      csr_pmp_mseccfg_i = {$random};
      debug_mode_i    = $random;
      priv_mode_i     = {$random};
      pmp_req_addr_i  = {$random,$random,$random};
      pmp_req_type_i  = {$random};
      #5;
    end
    $finish;
  end
endmodule
