"""
analyzer.py
-----------
Turns a ParsedModule (from app.parser) into a structural summary:
counts, a signal-driver map, and a consolidated list of warnings/errors.

Everything here is derived directly and deterministically from the parsed
structure. Nothing is estimated, guessed, or presented as a timing/area/
power number.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.parser.verilog_parser import ParsedModule, ParseIssue


@dataclass
class AnalysisResult:
    module_name: str
    num_ports: int
    num_inputs: int
    num_outputs: int
    num_inout: int
    num_wires: int
    num_regs: int
    num_parameters: int
    num_assigns: int
    num_always_blocks: int
    num_sequential_blocks: int
    num_combinational_blocks: int
    total_operators: int
    operator_counts: dict
    issues: list[ParseIssue] = field(default_factory=list)
    undriven_signals: list = field(default_factory=list)
    unread_signals: list = field(default_factory=list)

    def summary_rows(self) -> list[tuple[str, str]]:
        """(label, value) pairs for display in a table widget."""
        return [
            ("Module", self.module_name),
            ("Ports (total)", str(self.num_ports)),
            ("  Inputs", str(self.num_inputs)),
            ("  Outputs", str(self.num_outputs)),
            ("  Inout", str(self.num_inout)),
            ("Internal wires", str(self.num_wires)),
            ("Internal regs", str(self.num_regs)),
            ("Parameters", str(self.num_parameters)),
            ("Continuous assigns", str(self.num_assigns)),
            ("Always blocks", str(self.num_always_blocks)),
            ("  Sequential", str(self.num_sequential_blocks)),
            ("  Combinational", str(self.num_combinational_blocks)),
            ("Total operators", str(self.total_operators)),
            ("Errors", str(len([i for i in self.issues if i.severity == "error"]))),
            ("Warnings", str(len([i for i in self.issues if i.severity == "warning"]))),
        ]


class DesignAnalyzer:
    def analyze(self, mod: ParsedModule) -> AnalysisResult:
        inputs = [p for p in mod.ports if p.direction == "input"]
        outputs = [p for p in mod.ports if p.direction == "output"]
        inouts = [p for p in mod.ports if p.direction == "inout"]
        wires = [s for s in mod.signals if s.kind == "wire"]
        regs = [s for s in mod.signals if s.kind == "reg"]
        seq_blocks = [a for a in mod.always_blocks if a.is_sequential]
        comb_blocks = [a for a in mod.always_blocks if not a.is_sequential]

        issues = list(mod.issues)
        undriven, unread = self._driver_analysis(mod, issues)

        return AnalysisResult(
            module_name=mod.name,
            num_ports=len(mod.ports),
            num_inputs=len(inputs),
            num_outputs=len(outputs),
            num_inout=len(inouts),
            num_wires=len(wires),
            num_regs=len(regs),
            num_parameters=len(mod.parameters),
            num_assigns=len(mod.assigns),
            num_always_blocks=len(mod.always_blocks),
            num_sequential_blocks=len(seq_blocks),
            num_combinational_blocks=len(comb_blocks),
            total_operators=sum(mod.operator_counts.values()),
            operator_counts=dict(mod.operator_counts),
            issues=issues,
            undriven_signals=undriven,
            unread_signals=unread,
        )

    # -----------------------------------------------------------------
    def _driver_analysis(self, mod: ParsedModule, issues: list[ParseIssue]):
        """Flags internal signals that are declared but never driven, and
        outputs that are declared but never assigned anywhere. This is a
        simple, honest text-presence check -- it does not resolve
        conditional/partial drives across always blocks."""
        driven = set()
        for a in mod.assigns:
            lhs = a.lhs.split("[")[0].strip()
            driven.add(lhs)
        for ab in mod.always_blocks:
            for s in ab.assigned_signals:
                driven.add(s)

        read = set()
        import re
        for a in mod.assigns:
            for name in re.findall(r"[A-Za-z_]\w*", a.rhs):
                read.add(name)
        for ab in mod.always_blocks:
            for name in re.findall(r"[A-Za-z_]\w*", ab.raw_body):
                read.add(name)

        undriven = []
        for s in mod.signals:
            if s.name not in driven:
                undriven.append(s.name)
        for p in mod.ports:
            if p.direction == "output" and p.name not in driven:
                undriven.append(p.name)

        unread = []
        input_names = {p.name for p in mod.ports if p.direction == "input"}
        for s in mod.signals:
            if s.name not in read:
                unread.append(s.name)

        for name in undriven:
            issues.append(ParseIssue(
                "warning",
                f"Signal '{name}' is declared but never driven (no assign or "
                "always-block writes to it in the supported subset).",
                category="design",
            ))
        return undriven, unread
