module mult12(input [11:0] a, input [11:0] b, output [23:0] p);
  wire [23:0] pp0 = b[0] ? ({12'b0, a} << 0) : 24'b0;
  wire [23:0] pp1 = b[1] ? ({12'b0, a} << 1) : 24'b0;
  wire [23:0] pp2 = b[2] ? ({12'b0, a} << 2) : 24'b0;
  wire [23:0] pp3 = b[3] ? ({12'b0, a} << 3) : 24'b0;
  wire [23:0] pp4 = b[4] ? ({12'b0, a} << 4) : 24'b0;
  wire [23:0] pp5 = b[5] ? ({12'b0, a} << 5) : 24'b0;
  wire [23:0] pp6 = b[6] ? ({12'b0, a} << 6) : 24'b0;
  wire [23:0] pp7 = b[7] ? ({12'b0, a} << 7) : 24'b0;
  wire [23:0] pp8 = b[8] ? ({12'b0, a} << 8) : 24'b0;
  wire [23:0] pp9 = b[9] ? ({12'b0, a} << 9) : 24'b0;
  wire [23:0] pp10 = b[10] ? ({12'b0, a} << 10) : 24'b0;
  wire [23:0] pp11 = b[11] ? ({12'b0, a} << 11) : 24'b0;
  assign p = pp0 + pp1 + pp2 + pp3 + pp4 + pp5 + pp6 + pp7 + pp8 + pp9 + pp10 + pp11;
endmodule
