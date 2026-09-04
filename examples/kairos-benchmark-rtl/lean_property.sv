module lean_property(input logic a, input logic b, output logic y);
  assign y = (a & b) | (a & ~b);
  y_matches_a: assert property (y == a);
endmodule
