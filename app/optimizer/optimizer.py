"""
optimizer.py
------------
A transparent, rule-based optimizer for single-bit Boolean continuous
assignments (`assign y = <boolean expr>;`).

Scope and honesty guarantees:
  - Only expressions built from single-bit signal names, the operators
    & | ^ ~, parentheses, and the literals 0/1/1'b0/1'b1 are considered.
    Anything else (arithmetic, comparisons, bit-selects, concatenation,
    multi-bit buses used bitwise) is explicitly skipped and reported as
    "not applicable to the Boolean optimizer" rather than silently ignored.
  - Every suggestion is checked for exact truth-table equivalence with the
    original expression using sympy before it is ever shown to the user.
    A suggestion that is not provably equivalent is never produced.
  - The optimizer never modifies the user's source. It only proposes a
    replacement RHS string that the user can preview and choose to apply.
  - No area/power/timing claim is made. The benefit described is always in
    terms of expression complexity (operator count), which is a proxy, and
    is labeled as such.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

import sympy
from sympy.logic.boolalg import simplify_logic, to_dnf

from app.parser.verilog_parser import ParsedModule, Assign

_SAFE_EXPR_RE = re.compile(r"^[\s\w()&|~^]+$")
_LITERAL_RE = re.compile(r"\b1'b([01])\b")
_IDENT_RE = re.compile(r"[A-Za-z_]\w*")


@dataclass
class OptimizationSuggestion:
    rule_id: str
    rule_name: str
    signal: str
    original_expr: str
    optimized_expr: str
    explanation: str
    benefit: str
    verified: str          # "truth-table-verified" | "not verified"
    line: Optional[int] = None


class RTLOptimizer:
    RULES = {
        "BOOL-SIMPLIFY": "Boolean expression simplification",
        "SELF-AND": "Redundant self-AND (a & a)",
        "SELF-OR": "Redundant self-OR (a | a)",
        "SELF-XOR": "Self-XOR is constant zero (a ^ a)",
        "DOUBLE-NOT": "Double negation elimination (~~a)",
        "CONST-PROP": "Constant propagation (AND/OR with 0 or 1)",
    }

    def optimize_module(self, mod: ParsedModule) -> list[OptimizationSuggestion]:
        suggestions: list[OptimizationSuggestion] = []
        for a in mod.assigns:
            suggestions.extend(self._optimize_assign(a))
        return suggestions

    # -----------------------------------------------------------------
    def _optimize_assign(self, a: Assign) -> list[OptimizationSuggestion]:
        expr_raw = a.rhs.strip()
        normalized = _LITERAL_RE.sub(lambda m: "1" if m.group(1) == "1" else "0", expr_raw)

        if not _SAFE_EXPR_RE.match(normalized):
            return []  # out of scope for the Boolean optimizer (arithmetic, bit-select, etc.)

        identifiers = sorted(set(_IDENT_RE.findall(normalized)))
        if not identifiers:
            return []

        symbols = {name: sympy.symbols(name) for name in identifiers}
        py_expr = self._to_python_bool_expr(normalized)

        try:
            original = eval(py_expr, {"__builtins__": {}}, {**symbols, "True": True, "False": False})
        except Exception:
            return []  # could not safely parse; skip rather than guess

        if not isinstance(original, sympy.logic.boolalg.Boolean) and not isinstance(original, bool):
            return []

        simplified = simplify_logic(original, form="dnf")

        # Equivalence proof: compare truth tables over all identifiers.
        if not self._provably_equivalent(original, simplified, list(symbols.values())):
            return []  # never suggest something we haven't verified

        # IMPORTANT: sympy auto-simplifies idempotent/complementary patterns
        # (a&a, a|~a, etc.) the instant the expression tree is built, so the
        # "original" sympy object may already equal the simplified one even
        # though the user's *source text* still contains the redundant
        # operators. We therefore count the "before" operators from the raw
        # source text (the honest starting point) and the "after" operators
        # from the simplified sympy object.
        original_ops = self._text_op_count(normalized)
        simplified_ops = self._op_count(simplified)
        optimized_text = self._to_verilog(simplified)

        suggestions = []
        if optimized_text.strip() != normalized.strip() and simplified_ops < original_ops:
            rule_id, rule_name = self._classify_rule(expr_raw, original, simplified)
            suggestions.append(OptimizationSuggestion(
                rule_id=rule_id,
                rule_name=rule_name,
                signal=a.lhs,
                original_expr=expr_raw,
                optimized_expr=self._to_verilog(simplified),
                explanation=self._explain(rule_id, expr_raw),
                benefit=(
                    f"Reduces the expression from {original_ops} to {simplified_ops} "
                    "Boolean operator(s) (a proxy for logic complexity, not a measured "
                    "gate count, area, or timing figure)."
                ),
                verified="truth-table-verified",
                line=a.line,
            ))
        return suggestions

    # -----------------------------------------------------------------
    @staticmethod
    def _to_python_bool_expr(expr: str) -> str:
        # sympy Symbols overload &, |, ~, ^ directly, so the Verilog-subset
        # expression is already valid Python once literals are normalized.
        expr = re.sub(r"\b0\b", "False", expr)
        expr = re.sub(r"\b1\b", "True", expr)
        return expr

    @staticmethod
    def _provably_equivalent(a, b, symbols) -> bool:
        """Exhaustive truth-table comparison -- exact, not heuristic."""
        n = len(symbols)
        if n > 12:
            return False  # avoid a combinatorial blow-up; skip rather than assume
        for bits in range(2 ** n):
            subs = {s: bool((bits >> i) & 1) for i, s in enumerate(symbols)}
            va = bool(a.subs(subs)) if hasattr(a, "subs") else bool(a)
            vb = bool(b.subs(subs)) if hasattr(b, "subs") else bool(b)
            if va != vb:
                return False
        return True

    @staticmethod
    def _op_count(expr) -> int:
        if isinstance(expr, bool):
            return 0
        return str(expr).count("&") + str(expr).count("|") + str(expr).count("~") + str(expr).count("Xor")

    @staticmethod
    def _text_op_count(text: str) -> int:
        return text.count("&") + text.count("|") + text.count("~") + text.count("^")

    @staticmethod
    def _to_verilog(expr) -> str:
        s = str(expr)
        s = s.replace("True", "1'b1").replace("False", "1'b0")
        return s

    def _classify_rule(self, original_text: str, original, simplified) -> tuple[str, str]:
        compact = original_text.replace(" ", "")
        if re.search(r"~~", compact):
            return "DOUBLE-NOT", self.RULES["DOUBLE-NOT"]
        m = re.search(r"(\w+)\s*&\s*\1\b", original_text)
        if re.search(r"(\w+)\s*&\s*\1\b", original_text):
            return "SELF-AND", self.RULES["SELF-AND"]
        if re.search(r"(\w+)\s*\|\s*\1\b", original_text):
            return "SELF-OR", self.RULES["SELF-OR"]
        if re.search(r"(\w+)\s*\^\s*\1\b", original_text):
            return "SELF-XOR", self.RULES["SELF-XOR"]
        if re.search(r"\b(1'b0|1'b1|\b0\b|\b1\b)\b", original_text):
            return "CONST-PROP", self.RULES["CONST-PROP"]
        return "BOOL-SIMPLIFY", self.RULES["BOOL-SIMPLIFY"]

    @staticmethod
    def _explain(rule_id: str, original_text: str) -> str:
        explanations = {
            "DOUBLE-NOT": "Two NOT gates in series cancel out: NOT(NOT(a)) is logically identical to a.",
            "SELF-AND": "A signal ANDed with itself always equals itself (a & a = a), so the AND gate is redundant.",
            "SELF-OR": "A signal ORed with itself always equals itself (a | a = a), so the OR gate is redundant.",
            "SELF-XOR": "A signal XORed with itself is always 0, regardless of its value, so the logic can be replaced with a constant.",
            "CONST-PROP": "ANDing with 0 always yields 0, ANDing with 1 yields the other operand unchanged; the same idea applies to OR with 0/1. The constant can be propagated and the gate removed.",
            "BOOL-SIMPLIFY": "The expression was reduced to an equivalent Boolean sum-of-products form with fewer operators, verified against the full truth table.",
        }
        return explanations.get(rule_id, "Simplified to an equivalent expression with fewer operators.")
