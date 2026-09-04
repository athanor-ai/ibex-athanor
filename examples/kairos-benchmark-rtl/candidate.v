module candidate #(
    parameter WIDTH = 4
)(
    input  wire [WIDTH-1:0] a,
    input  wire [WIDTH-1:0] b,
    input  wire             sel,
    output wire [WIDTH-1:0] y
);
    assign y = sel ? (a - b) : (a + b);
endmodule
