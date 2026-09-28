from app.parser.verilog_parser import VerilogParser
from app.analyzer.analyzer import DesignAnalyzer


def _analyze(src):
    m = VerilogParser().parse(src)[0]
    return DesignAnalyzer().analyze(m)


def test_counts_ports_and_signals():
    src = """
    module counts(input wire a, input wire b, output reg y);
        wire internal_wire;
        reg internal_reg;
        assign internal_wire = a & b;
        always @(*) y = internal_wire;
    endmodule
    """
    r = _analyze(src)
    assert r.num_inputs == 2
    assert r.num_outputs == 1
    assert r.num_wires == 1
    assert r.num_regs == 1
    assert r.num_assigns == 1
    assert r.num_always_blocks == 1
    assert r.num_combinational_blocks == 1


def test_sequential_vs_combinational_split():
    src = """
    module m(input wire clk, input wire a, output reg y1, output reg y2);
        always @(posedge clk) y1 <= a;
        always @(*) y2 = a;
    endmodule
    """
    r = _analyze(src)
    assert r.num_sequential_blocks == 1
    assert r.num_combinational_blocks == 1


def test_undriven_output_flagged():
    src = """
    module m(input wire a, output reg y, output reg unused_out);
        always @(*) y = a;
    endmodule
    """
    r = _analyze(src)
    assert "unused_out" in r.undriven_signals


def test_summary_rows_contains_module_name():
    src = "module tiny(input wire a, output wire y); assign y = a; endmodule"
    r = _analyze(src)
    rows = dict(r.summary_rows())
    assert rows["Module"] == "tiny"
    assert rows["Continuous assigns"] == "1"
