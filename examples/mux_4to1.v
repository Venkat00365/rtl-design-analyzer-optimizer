// mux_4to1.v
// A 4-to-1 multiplexer built from continuous-assignment Boolean logic
// (rather than a case statement) so it also demonstrates the Boolean
// optimizer's ability to simplify a sum-of-products expression.
module mux_4to1 (
    input  wire d0,
    input  wire d1,
    input  wire d2,
    input  wire d3,
    input  wire s0,
    input  wire s1,
    output wire y
);
    assign y = (~s1 & ~s0 & d0) | (~s1 & s0 & d1) | (s1 & ~s0 & d2) | (s1 & s0 & d3);
endmodule
