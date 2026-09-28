// counter_fsm.v
// A 4-bit synchronous up-counter with synchronous active-high reset and
// an enable input. Demonstrates a sequential always block.
module counter_fsm (
    input  wire       clk,
    input  wire       rst,
    input  wire       en,
    output reg  [3:0] count
);
    always @(posedge clk) begin
        if (rst)
            count <= 4'b0000;
        else if (en)
            count <= count + 1'b1;
    end
endmodule
