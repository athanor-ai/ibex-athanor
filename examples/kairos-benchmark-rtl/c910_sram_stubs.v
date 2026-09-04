// Benchmark blackbox stubs for the absent OpenC910 vendor SRAM macros.
module ct_spsram_1024x32 (
  input  [9:0]  A,   input        CEN, input       CLK,
  input  [31:0] D,   input        GWEN, output reg [31:0] Q,
  input  [31:0] WEN
);
  reg [31:0] mem [0:1023];
  always @(posedge CLK) begin
    if (!CEN) begin
      if (!GWEN) mem[A] <= (D & ~WEN) | (mem[A] & WEN);
      Q <= mem[A];
    end
  end
endmodule

module ct_spsram_1024x33 (
  input  [9:0]  A,   input        CEN, input       CLK,
  input  [32:0] D,   input        GWEN, output reg [32:0] Q,
  input  [32:0] WEN
);
  reg [32:0] mem [0:1023];
  always @(posedge CLK) begin
    if (!CEN) begin
      if (!GWEN) mem[A] <= (D & ~WEN) | (mem[A] & WEN);
      Q <= mem[A];
    end
  end
endmodule
