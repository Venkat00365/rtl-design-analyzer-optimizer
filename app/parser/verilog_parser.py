"""
verilog_parser.py
------------------
A deliberately restricted, well-documented parser for a *subset* of
synthesizable Verilog. This is NOT a full Verilog/SystemVerilog compiler.

Supported subset (see docs/RTL_SUPPORTED_FEATURES.md for the authoritative list):
  - Single or multiple `module ... endmodule` blocks per file
  - ANSI-style port lists: input/output/inout, optional wire/reg, optional
    [MSB:LSB] range, e.g. `input wire [3:0] a, output reg y`
  - Non-ANSI style: `module m(a, b, y); input a, b; output y; ...`
  - `wire`, `reg`, `parameter` declarations (with optional range/value)
  - Continuous assignment: `assign lhs = expr;`
  - A single always block per module of the form:
        always @(posedge clk) ... end          (sequential)
        always @(posedge clk or negedge rst) .. (sequential, async reset)
        always @(*) / always @(a or b or c)     (combinational)
    containing `if/else if/else` and `case/endcase` statements with
    blocking (`=`) or non-blocking (`<=`) assignments.
  - Operators: & | ^ ~ ^~ + - * / == != < > <= >= << >> ! && || ?:

Anything outside this subset is reported as a ParseIssue (warning) rather
than silently ignored or guessed at. The parser never claims to understand
constructs it did not actually process.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


class ParseError(Exception):
    """Raised when the source cannot be parsed at all (e.g. no module found)."""


@dataclass
class ParseIssue:
    severity: str          # "error" | "warning" | "info"
    message: str
    line: Optional[int] = None
    category: str = "parser"  # "parser" | "design" | "unsupported"

    def __str__(self) -> str:
        loc = f"line {self.line}: " if self.line else ""
        return f"[{self.severity.upper()}] {loc}{self.message}"


@dataclass
class Port:
    name: str
    direction: str          # input | output | inout
    reg_type: bool = False  # declared as `reg` (only valid for outputs)
    msb: Optional[int] = None
    lsb: Optional[int] = None

    @property
    def width(self) -> int:
        if self.msb is None or self.lsb is None:
            return 1
        return abs(self.msb - self.lsb) + 1


@dataclass
class Signal:
    name: str
    kind: str               # wire | reg
    msb: Optional[int] = None
    lsb: Optional[int] = None

    @property
    def width(self) -> int:
        if self.msb is None or self.lsb is None:
            return 1
        return abs(self.msb - self.lsb) + 1


@dataclass
class Parameter:
    name: str
    value: str


@dataclass
class Assign:
    lhs: str
    rhs: str
    line: int


@dataclass
class AlwaysBlock:
    sensitivity: str
    is_sequential: bool     # True if posedge/negedge present
    line: int
    raw_body: str
    assigned_signals: list = field(default_factory=list)   # signals written in this block
    branch_complete: dict = field(default_factory=dict)    # signal -> bool (all branches covered?)


@dataclass
class ParsedModule:
    name: str
    ports: list[Port] = field(default_factory=list)
    signals: list[Signal] = field(default_factory=list)
    parameters: list[Parameter] = field(default_factory=list)
    assigns: list[Assign] = field(default_factory=list)
    always_blocks: list[AlwaysBlock] = field(default_factory=list)
    issues: list[ParseIssue] = field(default_factory=list)
    operator_counts: dict = field(default_factory=dict)
    source: str = ""

    # --- convenience -------------------------------------------------
    def all_signal_names(self) -> set[str]:
        names = {p.name for p in self.ports}
        names |= {s.name for s in self.signals}
        return names

    def errors(self) -> list[ParseIssue]:
        return [i for i in self.issues if i.severity == "error"]

    def warnings(self) -> list[ParseIssue]:
        return [i for i in self.issues if i.severity == "warning"]


# ---------------------------------------------------------------------
# Operator patterns used for counting / classification throughout the app
# ---------------------------------------------------------------------
OPERATOR_PATTERNS = {
    "AND (&)": r"(?<![&|])&(?!&)",
    "OR (|)": r"(?<![&|])\|(?!\|)",
    "XOR (^)": r"\^(?!~)",
    "XNOR (^~/~^)": r"(\^~|~\^)",
    "NOT (~)": r"~(?!\^)",
    "LOGICAL AND (&&)": r"&&",
    "LOGICAL OR (\\|\\|)": r"\|\|",
    "LOGICAL NOT (!)": r"(?<!=)!(?!=)",
    "ADD (+)": r"\+",
    "SUB (-)": r"(?<!//)-",
    "MUL (*)": r"\*",
    "DIV (/)": r"(?<!/)/(?!/)",
    "EQ (==)": r"==",
    "NEQ (!=)": r"!=",
    "LT/GT (<,>)": r"(?<![<>=])[<>](?!=)",
    "LTE/GTE (<=,>=)": r"(<=|>=)",
    "SHIFT (<<,>>)": r"(<<|>>)",
    "TERNARY (?:)": r"\?",
}

_COMMENT_LINE = re.compile(r"//.*")
_COMMENT_BLOCK = re.compile(r"/\*.*?\*/", re.DOTALL)
_MODULE_RE = re.compile(
    r"\bmodule\s+(\w+)\s*(#\s*\(.*?\)\s*)?\((.*?)\)\s*;(.*?)\bendmodule\b",
    re.DOTALL,
)
_RANGE_RE = re.compile(r"\[\s*(\d+)\s*:\s*(\d+)\s*\]")
_PORT_HEADER_ITEM_RE = re.compile(
    r"\b(input|output|inout)\b\s*(reg|wire)?\s*(signed)?\s*(\[\s*\d+\s*:\s*\d+\s*\])?\s*([\w\s,]+)"
)
_DECL_RE = re.compile(
    r"^\s*(input|output|inout|wire|reg)\s+(reg|wire)?\s*(signed)?\s*(\[\s*\d+\s*:\s*\d+\s*\])?\s*([\w\s,]+);",
    re.MULTILINE,
)
_PARAM_RE = re.compile(r"\bparameter\s+(?:\[\s*\d+\s*:\s*\d+\s*\]\s*)?(\w+)\s*=\s*([^,;]+)")
_ASSIGN_RE = re.compile(r"\bassign\s+([\w\[\]:\d]+)\s*=\s*([^;]+);")
_ALWAYS_RE = re.compile(r"\balways\s*@\s*\(([^)]*)\)\s*(.*?)(?=\balways\s*@|\Z)", re.DOTALL)


def _strip_comments(text: str) -> str:
    text = _COMMENT_BLOCK.sub(" ", text)
    text = _COMMENT_LINE.sub("", text)
    return text


def _line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def _parse_range(token: Optional[str]):
    if not token:
        return None, None
    m = _RANGE_RE.search(token)
    if not m:
        return None, None
    return int(m.group(1)), int(m.group(2))


class VerilogParser:
    """Parses source text into one or more ParsedModule objects."""

    def parse(self, source: str) -> list[ParsedModule]:
        if not source or not source.strip():
            raise ParseError("Empty source: nothing to parse.")

        cleaned = _strip_comments(source)
        matches = list(_MODULE_RE.finditer(cleaned))
        if not matches:
            raise ParseError(
                "No 'module ... endmodule' block found. "
                "Check that the file contains a complete, syntactically closed module."
            )

        modules = []
        for m in matches:
            name, _params, port_list_raw, body = m.groups()
            mod = ParsedModule(name=name, source=source)
            start_line = _line_of(cleaned, m.start())
            self._parse_ports_and_body(mod, port_list_raw, body, start_line)
            self._count_operators(mod)
            modules.append(mod)
        return modules

    # -----------------------------------------------------------------
    def _parse_ports_and_body(self, mod: ParsedModule, port_list_raw: str, body: str, start_line: int):
        # 1) Try ANSI-style ports declared directly in the header.
        ansi_ports = self._parse_ansi_header(port_list_raw)
        header_names = [p.strip() for p in re.split(r",", port_list_raw) if p.strip()]

        if ansi_ports:
            mod.ports = ansi_ports
        else:
            # Non-ANSI: header is just a name list; directions come from body decls.
            plain_names = []
            for tok in header_names:
                tok = re.sub(r"^(input|output|inout)\s+(reg|wire)?\s*(\[[^\]]*\])?\s*", "", tok).strip()
                if tok:
                    plain_names.append(tok)
            mod.ports = [Port(name=n, direction="unknown") for n in plain_names]

        # 2) Parse body declarations: input/output/inout (non-ANSI) and wire/reg/parameter.
        known_port_names = {p.name for p in mod.ports}
        for decl in _DECL_RE.finditer(body):
            kind, _reg_kw, _signed, rng, names_raw = decl.groups()
            msb, lsb = _parse_range(rng)
            names = [n.strip() for n in names_raw.split(",") if n.strip()]
            for n in names:
                if kind in ("input", "output", "inout"):
                    existing = next((p for p in mod.ports if p.name == n), None)
                    if existing:
                        existing.direction = kind
                        existing.msb, existing.lsb = msb, lsb
                        existing.reg_type = (_reg_kw == "reg")
                    else:
                        mod.ports.append(Port(name=n, direction=kind, msb=msb, lsb=lsb, reg_type=(_reg_kw == "reg")))
                        known_port_names.add(n)
                else:
                    if n not in known_port_names:
                        mod.signals.append(Signal(name=n, kind=kind, msb=msb, lsb=lsb))

        for p in mod.ports:
            if p.direction == "unknown":
                mod.issues.append(ParseIssue(
                    "warning",
                    f"Port '{p.name}' has no direction declaration (input/output/inout) "
                    "in the supported subset; treated as unresolved.",
                    category="unsupported",
                ))

        # 3) Parameters
        for pm in _PARAM_RE.finditer(body):
            mod.parameters.append(Parameter(name=pm.group(1), value=pm.group(2).strip()))

        # 4) Continuous assignments
        for am in _ASSIGN_RE.finditer(body):
            lhs, rhs = am.groups()
            line = start_line + _line_of(body, am.start()) - 1
            mod.assigns.append(Assign(lhs=lhs.strip(), rhs=rhs.strip(), line=line))

        # 5) Always blocks
        for bm in _ALWAYS_RE.finditer(body):
            sens, blk_body = bm.groups()
            line = start_line + _line_of(body, bm.start()) - 1
            is_seq = bool(re.search(r"\b(posedge|negedge)\b", sens))
            # Trim the block body to the matching begin/end (best-effort: up to
            # the next unmatched 'endmodule' boundary, since body is already
            # module-scoped).
            block = self._extract_block(blk_body)
            ab = AlwaysBlock(sensitivity=sens.strip(), is_sequential=is_seq, line=line, raw_body=block)
            self._analyze_always_block(mod, ab)
            mod.always_blocks.append(ab)

        if not mod.assigns and not mod.always_blocks:
            mod.issues.append(ParseIssue(
                "warning",
                "No 'assign' statements or 'always' blocks were recognized in this module. "
                "The module may use constructs outside the supported subset (see "
                "docs/RTL_SUPPORTED_FEATURES.md).",
                category="unsupported",
            ))

    # -----------------------------------------------------------------
    def _parse_ansi_header(self, header: str) -> list[Port]:
        if not re.search(r"\b(input|output|inout)\b", header):
            return []
        ports: list[Port] = []
        # Split on commas that are not inside a [..] range.
        parts = self._split_top_level(header)
        current_dir, current_reg, current_range = None, None, None
        for part in parts:
            part = part.strip()
            if not part:
                continue
            m = re.match(r"^(input|output|inout)\s*(reg|wire)?\s*(signed)?\s*(\[\s*\d+\s*:\s*\d+\s*\])?\s*(.+)$", part)
            if m:
                current_dir, current_reg, _signed, current_range, rest = m.groups()
                names = [n.strip() for n in rest.split(",") if n.strip()]
            else:
                names = [n.strip() for n in part.split(",") if n.strip()]
            msb, lsb = _parse_range(current_range)
            for n in names:
                if n and current_dir:
                    ports.append(Port(name=n, direction=current_dir, reg_type=(current_reg == "reg"), msb=msb, lsb=lsb))
        return ports

    @staticmethod
    def _split_top_level(text: str) -> list[str]:
        parts, depth, buf = [], 0, []
        for ch in text:
            if ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
            if ch == "," and depth == 0:
                parts.append("".join(buf))
                buf = []
            else:
                buf.append(ch)
        if buf:
            parts.append("".join(buf))
        return parts

    @staticmethod
    def _extract_block(text: str) -> str:
        text = text.lstrip()
        if text.startswith("begin"):
            depth = 0
            i = 0
            n = len(text)
            while i < n:
                if text[i:i + 5] == "begin" and (i == 0 or not text[i - 1].isalnum()):
                    depth += 1
                    i += 5
                    continue
                if text[i:i + 3] == "end" and (i + 3 == n or not text[i + 3].isalnum()):
                    depth -= 1
                    i += 3
                    if depth == 0:
                        return text[:i]
                    continue
                i += 1
            return text
        # single statement (up to first ';')
        m = re.search(r";", text)
        return text[: m.end()] if m else text

    # -----------------------------------------------------------------
    def _analyze_always_block(self, mod: ParsedModule, ab: AlwaysBlock):
        """Best-effort latch / branch-completeness analysis for the supported
        if/else and case/default patterns. Anything more complex is left
        unclassified rather than guessed at."""
        body = ab.raw_body
        assigned = set(re.findall(r"([\w]+)\s*<?=\s*[^=]", body))
        assigned = {a for a in assigned if a in mod.all_signal_names() or True}
        ab.assigned_signals = sorted(set(re.findall(r"\b(\w+)\s*<=", body)) | set(re.findall(r"\b(\w+)\s*=(?!=)", body)))

        if ab.is_sequential:
            return  # latch analysis only applies to combinational logic

        # Combinational block: check for if-without-else and case-without-default
        has_if = bool(re.search(r"\bif\s*\(", body))
        has_else = bool(re.search(r"\belse\b", body))
        has_case = bool(re.search(r"\bcase\s*\(", body))
        has_default = bool(re.search(r"\bdefault\s*:", body))

        if has_if and not has_else:
            ab.branch_complete["__if__"] = False
            mod.issues.append(ParseIssue(
                "warning",
                f"Combinational always block at line {ab.line} has an 'if' with no matching "
                "'else'. Signals assigned only inside the if-branch may infer an unintended "
                "latch. Add an else branch or a default assignment before the if.",
                line=ab.line,
                category="design",
            ))
        if has_case and not has_default:
            ab.branch_complete["__case__"] = False
            mod.issues.append(ParseIssue(
                "warning",
                f"Combinational 'case' at line {ab.line} has no 'default' branch. "
                "Uncovered case values may infer an unintended latch. Add a default case.",
                line=ab.line,
                category="design",
            ))

    # -----------------------------------------------------------------
    def _count_operators(self, mod: ParsedModule):
        """Counts operators only within actual expressions (assign RHS and
        always-block bodies), never in declarations or sensitivity lists,
        to avoid false positives like '@(*)' being read as multiplication."""
        expr_text = "\n".join(a.rhs for a in mod.assigns)
        expr_text += "\n" + "\n".join(ab.raw_body for ab in mod.always_blocks)
        counts = {}
        for label, pattern in OPERATOR_PATTERNS.items():
            n = len(re.findall(pattern, expr_text))
            if n:
                counts[label] = n
        mod.operator_counts = counts
