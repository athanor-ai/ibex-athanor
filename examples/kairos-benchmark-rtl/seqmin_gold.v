module seqmin(input clk, input [7:0] d, output reg [7:0] q);
  reg [7:0] s1;
  always @(posedge clk) begin
    s1 <= d + 8'd1;
    q  <= s1;
  end
endmodule
