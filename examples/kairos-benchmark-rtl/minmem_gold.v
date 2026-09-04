module minmem(input clk, input we, input [3:0] addr, input [7:0] din, output [7:0] dout);
  reg [7:0] mem [0:15];
  always @(posedge clk) if (we) mem[addr] <= din;
  assign dout = mem[addr];
endmodule
