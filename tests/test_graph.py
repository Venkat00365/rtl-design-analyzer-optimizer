from app.parser.verilog_parser import VerilogParser
from app.visualization.graph_builder import CircuitGraphBuilder


def test_graph_contains_all_ports_as_nodes():
    src = "module m(input wire a, input wire b, output wire y); assign y = a & b; endmodule"
    m = VerilogParser().parse(src)[0]
    g = CircuitGraphBuilder().build(m)
    assert {"a", "b", "y"}.issubset(set(g.nodes))


def test_graph_has_edges_from_inputs_to_output_via_logic_node():
    src = "module m(input wire a, input wire b, output wire y); assign y = a & b; endmodule"
    m = VerilogParser().parse(src)[0]
    g = CircuitGraphBuilder().build(m)
    logic_nodes = [n for n, d in g.nodes(data=True) if d.get("kind") == "logic"]
    assert len(logic_nodes) == 1
    logic = logic_nodes[0]
    assert g.has_edge("a", logic)
    assert g.has_edge("b", logic)
    assert g.has_edge(logic, "y")


def test_graph_renders_to_png(tmp_path):
    src = "module m(input wire a, output wire y); assign y = ~a; endmodule"
    m = VerilogParser().parse(src)[0]
    gb = CircuitGraphBuilder()
    g = gb.build(m)
    out = tmp_path / "graph.png"
    gb.render_png(g, str(out))
    assert out.exists()
    assert out.stat().st_size > 0
