from app.parser.verilog_parser import VerilogParser
from app.optimizer.optimizer import RTLOptimizer


def _optimize(src):
    m = VerilogParser().parse(src)[0]
    return RTLOptimizer().optimize_module(m)


def test_self_and_is_simplified():
    src = "module m(input wire a, output wire y); assign y = a & a; endmodule"
    sugg = _optimize(src)
    assert len(sugg) == 1
    assert sugg[0].rule_id == "SELF-AND"
    assert sugg[0].optimized_expr == "a"


def test_self_or_is_simplified():
    src = "module m(input wire a, output wire y); assign y = a | a; endmodule"
    sugg = _optimize(src)
    assert sugg[0].rule_id == "SELF-OR"
    assert sugg[0].optimized_expr == "a"


def test_self_xor_is_constant_zero():
    src = "module m(input wire a, output wire y); assign y = a ^ a; endmodule"
    sugg = _optimize(src)
    assert sugg[0].rule_id == "SELF-XOR"
    assert sugg[0].optimized_expr == "1'b0"


def test_double_negation_eliminated():
    src = "module m(input wire a, output wire y); assign y = ~~a; endmodule"
    sugg = _optimize(src)
    assert sugg[0].rule_id == "DOUBLE-NOT"
    assert sugg[0].optimized_expr == "a"


def test_constant_propagation_or_zero():
    src = "module m(input wire a, output wire y); assign y = a | 1'b0; endmodule"
    sugg = _optimize(src)
    assert sugg[0].rule_id == "CONST-PROP"
    assert sugg[0].optimized_expr == "a"


def test_sum_of_products_reduction_is_correct():
    src = "module m(input wire a, input wire b, output wire y); assign y = (a & b) | (a & ~b); endmodule"
    sugg = _optimize(src)
    assert len(sugg) == 1
    assert sugg[0].optimized_expr == "a"
    # Independently verify equivalence with a from-scratch truth table (oracle
    # written without using the optimizer's own sympy machinery).
    for a_val in (0, 1):
        for b_val in (0, 1):
            original = (a_val & b_val) | (a_val & (1 - b_val))
            assert bool(original) == bool(a_val)


def test_no_suggestion_for_irreducible_mux_expression():
    # A genuine 4:1 mux with independent data lines has no redundant logic.
    src = (
        "module m(input wire d0, input wire d1, input wire d2, input wire d3, "
        "input wire s0, input wire s1, output wire y); "
        "assign y = (~s1 & ~s0 & d0) | (~s1 & s0 & d1) | (s1 & ~s0 & d2) | (s1 & s0 & d3); "
        "endmodule"
    )
    sugg = _optimize(src)
    assert sugg == []


def test_no_suggestion_for_arithmetic_expressions():
    # Out of scope for the Boolean optimizer -- must be skipped, not guessed at.
    src = "module m(input wire [3:0] a, input wire [3:0] b, output wire [3:0] y); assign y = a + b; endmodule"
    sugg = _optimize(src)
    assert sugg == []


def test_every_suggestion_is_marked_verified():
    src = """
    module m(input wire a, input wire b, output wire y1, output wire y2);
        assign y1 = a & a;
        assign y2 = (a & b) | (a & ~b);
    endmodule
    """
    sugg = _optimize(src)
    assert len(sugg) == 2
    assert all(s.verified == "truth-table-verified" for s in sugg)
