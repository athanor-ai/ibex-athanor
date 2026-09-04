module seqflop(input clk, input rst_n, input [7:0] d, input en, output reg [7:0] q);
  reg [7:0] stage1;
  always @(posedge clk) begin
    if (!rst_n) begin stage1 <= 8'h00; q <= 8'h00; end
    else begin
      if (en) stage1 <= d + 8'd2;   // BUG: increments by 2
      q <= stage1;
    end
  end
endmodule
