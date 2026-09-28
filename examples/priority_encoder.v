// priority_encoder.v
// 4-to-2 priority encoder: encodes the highest-priority active input
// into a 2-bit code and asserts 'valid' if any input is active.
module priority_encoder (
    input  wire [3:0] in,
    output reg  [1:0] code,
    output reg        valid
);
    always @(*) begin
        valid = 1'b1;
        if (in[3])
            code = 2'b11;
        else if (in[2])
            code = 2'b10;
        else if (in[1])
            code = 2'b01;
        else if (in[0])
            code = 2'b00;
        else begin
            code = 2'b00;
            valid = 1'b0;
        end
    end
endmodule
