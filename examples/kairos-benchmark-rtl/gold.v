module gold #(
    parameter WIDTH = 4
)(
    input  wire [WIDTH-1:0] a,
    input  wire [WIDTH-1:0] b,
    input  wire             sel,
    output wire [WIDTH-1:0] y
);
    wire [WIDTH-1:0] add_out;
    wire [WIDTH-1:0] sub_out;
    assign add_out = a + b;
    assign sub_out = a - b;
    assign y = sel ? sub_out : add_out;
endmodule
