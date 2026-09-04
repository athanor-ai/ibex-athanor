module sequni(input clk, input rst_n, input [7:0] d, output reg [7:0] q);
  reg [7:0] s1;
  always @(posedge clk) begin
    if (!rst_n) begin s1 <= 8'h0; q <= 8'h0; end
    else begin s1 <= d + 8'd2; q <= s1; end
  end
endmodule
