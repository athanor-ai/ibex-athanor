module seqrst(input clk, input rst_n, input [7:0] d, output reg [7:0] q);
  reg [7:0] s1;
  wire [7:0] inc = d + 8'd1;
  always @(posedge clk) begin
    if (!rst_n) s1 <= 8'h0; else s1 <= inc;
    q  <= s1;
  end
endmodule
