module crc8(input [7:0] d, input [7:0] c, output [7:0] o);
  wire [7:0] s = c ^ d;
  assign o = {s[6:0],1'b0} ^ (s[7] ? 8'h07 : 8'h00);
endmodule
