module minmem(input clk, input we, input [3:0] addr, input [7:0] din, output [7:0] dout);
  reg [7:0] mem [0:15];
  wire write_now = we;
  always @(posedge clk) begin
    if (write_now) mem[addr] <= din;
  end
  assign dout = mem[addr];
endmodule
