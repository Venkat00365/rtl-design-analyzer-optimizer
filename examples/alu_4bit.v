// alu_4bit.v
// A 4-bit ALU supporting add, subtract, bitwise AND, and bitwise OR,
// selected by a 2-bit opcode. Combinational, single always block.
module alu_4bit (
    input  wire [3:0] a,
    input  wire [3:0] b,
    input  wire [1:0] op,
    output reg  [3:0] result
);
    always @(*) begin
        case (op)
            2'b00: result = a + b;
            2'b01: result = a - b;
            2'b10: result = a & b;
            2'b11: result = a | b;
            default: result = 4'b0000;
        endcase
    end
endmodule
