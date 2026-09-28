"""
graph_builder.py
----------------
Builds a NetworkX directed graph that reflects the *actual parsed* signals
and connections of a module: input ports, output ports, internal signals,
and one node per assignment/expression that drives a signal. This is a
signal-connectivity graph, not a fabricated schematic -- it will only ever
show what the parser actually understood.
"""
from __future__ import annotations

import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx

from app.parser.verilog_parser import ParsedModule

_IDENT_RE = re.compile(r"[A-Za-z_]\w*")

NODE_COLORS = {
    "input": "#4CAF50",
    "output": "#F44336",
    "inout": "#FF9800",
    "signal": "#2196F3",
    "logic": "#9E9E9E",
}


class CircuitGraphBuilder:
    def build(self, mod: ParsedModule) -> nx.DiGraph:
        g = nx.DiGraph(name=mod.name)

        for p in mod.ports:
            g.add_node(p.name, kind=p.direction, label=f"{p.name}\n[{p.width}b]" if p.width > 1 else p.name)
        for s in mod.signals:
            g.add_node(s.name, kind="signal", label=f"{s.name}\n[{s.width}b]" if s.width > 1 else s.name)

        for idx, a in enumerate(mod.assigns):
            lhs = a.lhs.split("[")[0].strip()
            logic_node = f"assign_{idx}_{lhs}"
            g.add_node(logic_node, kind="logic", label="assign")
            operands = self._operands(a.rhs, mod)
            for op in operands:
                if op in g:
                    g.add_edge(op, logic_node)
            if lhs in g:
                g.add_edge(logic_node, lhs)

        for idx, ab in enumerate(mod.always_blocks):
            logic_node = f"always_{idx}"
            kind = "logic"
            label = "always\n(seq)" if ab.is_sequential else "always\n(comb)"
            g.add_node(logic_node, kind=kind, label=label)
            operands = self._operands(ab.raw_body, mod)
            for op in operands:
                if op in g and op not in ab.assigned_signals:
                    g.add_edge(op, logic_node)
            for out_sig in ab.assigned_signals:
                if out_sig in g:
                    g.add_edge(logic_node, out_sig)

        return g

    @staticmethod
    def _operands(expr: str, mod: ParsedModule) -> set[str]:
        names = set(_IDENT_RE.findall(expr))
        valid = mod.all_signal_names()
        return {n for n in names if n in valid}

    # -----------------------------------------------------------------
    def render_png(self, g: nx.DiGraph, out_path: str, title: str = "") -> str:
        """Renders the graph to a PNG file and returns the path. Uses a
        layered layout when possible for readability; falls back to a
        spring layout for irregular graphs."""
        n_nodes = g.number_of_nodes()
        fig_w = max(8, min(24, n_nodes * 0.9))
        fig_h = max(6, min(16, n_nodes * 0.55))
        fig, ax = plt.subplots(figsize=(fig_w, fig_h))

        try:
            for layer, nodes in enumerate(nx.topological_generations(g)):
                for n in nodes:
                    g.nodes[n]["layer"] = layer
            pos = nx.multipartite_layout(g, subset_key="layer")
        except Exception:
            pos = nx.spring_layout(g, seed=42, k=1.2 / max(1, n_nodes ** 0.5))

        colors = [NODE_COLORS.get(g.nodes[n].get("kind", "signal"), "#9E9E9E") for n in g.nodes]
        labels = {n: g.nodes[n].get("label", n) for n in g.nodes}
        shapes_logic = [n for n in g.nodes if g.nodes[n].get("kind") == "logic"]
        shapes_other = [n for n in g.nodes if g.nodes[n].get("kind") != "logic"]

        nx.draw_networkx_nodes(g, pos, nodelist=shapes_other, ax=ax,
                                node_color=[NODE_COLORS.get(g.nodes[n]["kind"], "#9E9E9E") for n in shapes_other],
                                node_shape="o", node_size=1400, edgecolors="#222", linewidths=1.2)
        nx.draw_networkx_nodes(g, pos, nodelist=shapes_logic, ax=ax,
                                node_color=NODE_COLORS["logic"],
                                node_shape="s", node_size=1000, edgecolors="#222", linewidths=1.2)
        nx.draw_networkx_edges(g, pos, ax=ax, arrows=True, arrowsize=14,
                                edge_color="#666", width=1.4, connectionstyle="arc3,rad=0.05")
        nx.draw_networkx_labels(g, pos, labels=labels, ax=ax, font_size=8, font_weight="bold")

        legend_handles = [
            plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=c, markersize=12, label=k.capitalize())
            for k, c in NODE_COLORS.items()
        ]
        ax.legend(handles=legend_handles, loc="upper left", bbox_to_anchor=(1.01, 1.0), fontsize=9)
        ax.set_title(title or f"Circuit graph: {g.graph.get('name', '')}", fontsize=13)
        ax.axis("off")
        fig.tight_layout()
        fig.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return out_path
