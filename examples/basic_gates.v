// basic_gates.v
// A small combinational logic block demonstrating AND, OR, XOR and NAND
// gates built from primary inputs using continuous assignments.
module basic_gates (
    input  wire a,
    input  wire b,
    input  wire c,
    output wire y_and,
    output wire y_or,
    output wire y_xor,
    output wire y_nand
);
    assign y_and  = a & b;
    assign y_or   = a | b;
    assign y_xor  = a ^ b;
    assign y_nand = ~(a & b & c);
endmodule
