module ibex_branch_predict_gate (
  input  logic clk_i,
  input  logic rst_ni,


  input  logic [31:0] fetch_rdata_i,
  input  logic [31:0] fetch_pc_i,
  input  logic        fetch_valid_i,


  output logic        predict_branch_taken_o,
  output logic [31:0] predict_branch_pc_o
);

  wire [31:0] instr;
  assign instr = fetch_rdata_i;

  wire low_11;
  wire low_01;
  assign low_11 = instr[1] & instr[0];
  assign low_01 = (~instr[1]) & instr[0];

  wire instr_b;
  wire instr_j;
  wire instr_cb;
  wire instr_cj;

  assign instr_b  = low_11 & (instr[6:2] == 5'b11000);
  assign instr_j  = low_11 & (instr[6:2] == 5'b11011);
  assign instr_cb = low_01 & instr[15] & instr[14];
  assign instr_cj = low_01 & (~instr[14]) & instr[13];

  wire sel_comp;
  assign sel_comp = instr_cj | instr_cb;

  wire [31:0] branch_imm;

  assign branch_imm[0] = 1'b0;

  assign branch_imm[31] = sel_comp ? instr[12] : instr[31];
  assign branch_imm[30] = sel_comp ? instr[12] : instr[31];
  assign branch_imm[29] = sel_comp ? instr[12] : instr[31];
  assign branch_imm[28] = sel_comp ? instr[12] : instr[31];
  assign branch_imm[27] = sel_comp ? instr[12] : instr[31];
  assign branch_imm[26] = sel_comp ? instr[12] : instr[31];
  assign branch_imm[25] = sel_comp ? instr[12] : instr[31];
  assign branch_imm[24] = sel_comp ? instr[12] : instr[31];
  assign branch_imm[23] = sel_comp ? instr[12] : instr[31];
  assign branch_imm[22] = sel_comp ? instr[12] : instr[31];
  assign branch_imm[21] = sel_comp ? instr[12] : instr[31];
  assign branch_imm[20] = sel_comp ? instr[12] : instr[31];

  assign branch_imm[19] = instr_j ? instr[19] : (sel_comp ? instr[12] : instr[31]);
  assign branch_imm[18] = instr_j ? instr[18] : (sel_comp ? instr[12] : instr[31]);
  assign branch_imm[17] = instr_j ? instr[17] : (sel_comp ? instr[12] : instr[31]);
  assign branch_imm[16] = instr_j ? instr[16] : (sel_comp ? instr[12] : instr[31]);
  assign branch_imm[15] = instr_j ? instr[15] : (sel_comp ? instr[12] : instr[31]);
  assign branch_imm[14] = instr_j ? instr[14] : (sel_comp ? instr[12] : instr[31]);
  assign branch_imm[13] = instr_j ? instr[13] : (sel_comp ? instr[12] : instr[31]);
  assign branch_imm[12] = (instr_j | sel_comp) ? instr[12] : instr[31];

  assign branch_imm[11] = sel_comp ? instr[12] : (instr_j ? instr[20] : instr[7]);
  assign branch_imm[10] = instr_j ? instr[30] : (instr_cj ? instr[8]  : (instr_cb ? instr[12] : instr[30]));
  assign branch_imm[9]  = instr_j ? instr[29] : (instr_cj ? instr[10] : (instr_cb ? instr[12] : instr[29]));
  assign branch_imm[8]  = instr_j ? instr[28] : (instr_cj ? instr[9]  : (instr_cb ? instr[12] : instr[28]));
  assign branch_imm[7]  = instr_j ? instr[27] : (instr_cj ? instr[6]  : (instr_cb ? instr[6]  : instr[27]));
  assign branch_imm[6]  = instr_j ? instr[26] : (instr_cj ? instr[7]  : (instr_cb ? instr[5]  : instr[26]));
  assign branch_imm[5]  = instr_j ? instr[25] : (instr_cj ? instr[2]  : (instr_cb ? instr[2]  : instr[25]));
  assign branch_imm[4]  = instr_j ? instr[24] : (instr_cj ? instr[11] : (instr_cb ? instr[11] : instr[11]));
  assign branch_imm[3]  = instr_j ? instr[23] : (instr_cj ? instr[5]  : (instr_cb ? instr[10] : instr[10]));
  assign branch_imm[2]  = instr_j ? instr[22] : (instr_cj ? instr[4]  : (instr_cb ? instr[4]  : instr[9]));
  assign branch_imm[1]  = instr_j ? instr[21] : (instr_cj ? instr[3]  : (instr_cb ? instr[3]  : instr[8]));

  wire instr_b_taken;
  assign instr_b_taken = (instr_b & instr[31]) | (instr_cb & instr[12]);

  assign predict_branch_taken_o = fetch_valid_i & (instr_j | instr_cj | instr_b_taken);
  assign predict_branch_pc_o = fetch_pc_i + branch_imm;

endmodule
