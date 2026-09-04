module crc8(input [7:0] d, input [7:0] c, output [7:0] o);
  wire [7:0] s = c ^ d;
  wire f = s[7];
  assign o[0] = f;
  assign o[1] = s[0] ^ f;
  assign o[2] = s[1] ^ f;
  assign o[3] = s[2];
  assign o[4] = s[3];
  assign o[5] = s[4];
  assign o[6] = s[5];
  assign o[7] = s[6];
endmodule
