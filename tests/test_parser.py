import pytest

from app.parser.verilog_parser import VerilogParser, ParseError


def test_parses_simple_module_with_ansi_ports():
    src = """
    module simple(input wire a, input wire b, output wire y);
        assign y = a & b;
    endmodule
    """
    mods = VerilogParser().parse(src)
    assert len(mods) == 1
    m = mods[0]
    assert m.name == "simple"
    assert {p.name for p in m.ports} == {"a", "b", "y"}
    assert next(p for p in m.ports if p.name == "a").direction == "input"
    assert next(p for p in m.ports if p.name == "y").direction == "output"
    assert len(m.assigns) == 1
    assert m.assigns[0].lhs == "y"
    assert m.assigns[0].rhs == "a & b"


def test_parses_non_ansi_ports():
    src = """
    module m2(a, b, y);
        input a;
        input b;
        output y;
        assign y = a | b;
    endmodule
    """
    mods = VerilogParser().parse(src)
    m = mods[0]
    dirs = {p.name: p.direction for p in m.ports}
    assert dirs == {"a": "input", "b": "input", "y": "output"}


def test_parses_bit_widths():
    src = """
    module widths(input wire [3:0] a, output reg [7:0] y);
        always @(*) y = a;
    endmodule
    """
    m = VerilogParser().parse(src)[0]
    a = next(p for p in m.ports if p.name == "a")
    y = next(p for p in m.ports if p.name == "y")
    assert a.width == 4
    assert y.width == 8
    assert y.reg_type is True


def test_empty_source_raises():
    with pytest.raises(ParseError):
        VerilogParser().parse("")


def test_no_module_raises():
    with pytest.raises(ParseError):
        VerilogParser().parse("this is not verilog at all")


def test_detects_incomplete_if_latch_risk():
    src = """
    module latchy(input wire sel, input wire a, output reg y);
        always @(*) begin
            if (sel)
                y = a;
        end
    endmodule
    """
    m = VerilogParser().parse(src)[0]
    messages = [i.message for i in m.issues]
    assert any("no matching 'else'" in msg for msg in messages)


def test_detects_incomplete_case_latch_risk():
    src = """
    module casey(input wire [1:0] sel, output reg y);
        always @(*) begin
            case (sel)
                2'b00: y = 1'b0;
                2'b01: y = 1'b1;
            endcase
        end
    endmodule
    """
    m = VerilogParser().parse(src)[0]
    messages = [i.message for i in m.issues]
    assert any("no 'default'" in msg for msg in messages)


def test_complete_if_else_has_no_latch_warning():
    src = """
    module full(input wire sel, input wire a, input wire b, output reg y);
        always @(*) begin
            if (sel)
                y = a;
            else
                y = b;
        end
    endmodule
    """
    m = VerilogParser().parse(src)[0]
    messages = [i.message for i in m.issues]
    assert not any("no matching 'else'" in msg for msg in messages)


def test_sequential_always_block_detected():
    src = """
    module seq(input wire clk, input wire rst, output reg [3:0] q);
        always @(posedge clk) begin
            if (rst)
                q <= 4'b0000;
            else
                q <= q + 1'b1;
        end
    endmodule
    """
    m = VerilogParser().parse(src)[0]
    assert len(m.always_blocks) == 1
    assert m.always_blocks[0].is_sequential is True


def test_operator_counts_exclude_sensitivity_list():
    src = """
    module opcount(input wire a, input wire b, output reg y);
        always @(*) begin
            y = a & b;
        end
    endmodule
    """
    m = VerilogParser().parse(src)[0]
    # The '*' in always @(*) must never be counted as a multiplication operator.
    assert m.operator_counts.get("MUL (*)", 0) == 0
    assert m.operator_counts.get("AND (&)", 0) == 1


def test_multiple_modules_in_one_file():
    src = """
    module a1(input wire x, output wire y); assign y = x; endmodule
    module a2(input wire x, output wire y); assign y = ~x; endmodule
    """
    mods = VerilogParser().parse(src)
    assert {m.name for m in mods} == {"a1", "a2"}
