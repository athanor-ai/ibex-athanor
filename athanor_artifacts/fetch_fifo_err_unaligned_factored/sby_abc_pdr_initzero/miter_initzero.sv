module ibex_fetch_fifo_relation_seq_no_occupancy_miter_initzero (
  input wire        clk_i,
  input wire        rst_ni,
  input wire        clear_i,
  input wire        in_valid_i,
  input wire [31:0] in_addr_i,
  input wire [31:0] in_rdata_i,
  input wire        in_err_i,
  input wire        out_ready_i
);
  wire [1:0]  gold_busy_o, gate_busy_o;
  wire        gold_out_valid_o, gate_out_valid_o;
  wire [31:0] gold_out_addr_o, gate_out_addr_o;
  wire [31:0] gold_out_rdata_o, gate_out_rdata_o;
  wire        gold_out_err_o, gate_out_err_o;
  wire        gold_out_err_plus2_o, gate_out_err_plus2_o;
  wire [2:0]  gold_valid_q, gate_valid_q;
  wire [2:0]  gold_err_q, gate_err_q;
  wire [95:0] gold_rdata_q, gate_rdata_q;
  wire [31:1] gold_instr_addr_q, gate_instr_addr_q;

  ibex_fetch_fifo_gold gold (
    .clk_i(clk_i), .rst_ni(rst_ni), .clear_i(clear_i),
    .busy_o(gold_busy_o),
    .in_valid_i(in_valid_i), .in_addr_i(in_addr_i),
    .in_rdata_i(in_rdata_i), .in_err_i(in_err_i),
    .out_valid_o(gold_out_valid_o), .out_ready_i(out_ready_i),
    .out_addr_o(gold_out_addr_o), .out_rdata_o(gold_out_rdata_o),
    .out_err_o(gold_out_err_o), .out_err_plus2_o(gold_out_err_plus2_o),
    .__state_valid_q(gold_valid_q), .__state_err_q(gold_err_q),
    .__state_rdata_q(gold_rdata_q), .__state_instr_addr_q(gold_instr_addr_q)
  );

  ibex_fetch_fifo_gate gate (
    .clk_i(clk_i), .rst_ni(rst_ni), .clear_i(clear_i),
    .busy_o(gate_busy_o),
    .in_valid_i(in_valid_i), .in_addr_i(in_addr_i),
    .in_rdata_i(in_rdata_i), .in_err_i(in_err_i),
    .out_valid_o(gate_out_valid_o), .out_ready_i(out_ready_i),
    .out_addr_o(gate_out_addr_o), .out_rdata_o(gate_out_rdata_o),
    .out_err_o(gate_out_err_o), .out_err_plus2_o(gate_out_err_plus2_o),
    .__state_valid_q(gate_valid_q), .__state_err_q(gate_err_q),
    .__state_rdata_q(gate_rdata_q), .__state_instr_addr_q(gate_instr_addr_q)
  );

  initial begin
    assume (gold_valid_q == 3'b000);
    assume (gate_valid_q == 3'b000);
    assume (gold_err_q == 3'b000);
    assume (gate_err_q == 3'b000);
    assume (gold_rdata_q == 96'b0);
    assume (gate_rdata_q == 96'b0);
    assume (gold_instr_addr_q == 31'b0);
    assume (gate_instr_addr_q == 31'b0);
  end

  always @(posedge clk_i) begin
    assert (gold_valid_q == gate_valid_q);
    assert (gold_err_q == gate_err_q);
    assert (gold_rdata_q == gate_rdata_q);
    assert (gold_instr_addr_q == gate_instr_addr_q);
    assert (gold_busy_o == gate_busy_o);
    assert (gold_out_valid_o == gate_out_valid_o);
    assert (gold_out_addr_o == gate_out_addr_o);
    assert (gold_out_rdata_o == gate_out_rdata_o);
    assert (gold_out_err_o == gate_out_err_o);
    assert (gold_out_err_plus2_o == gate_out_err_plus2_o);
  end
endmodule
