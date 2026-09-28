# Optimization Methodology
Scope: single-bit Boolean `assign` statements using identifiers, `& | ^ ~`, parentheses and constants.
1. Expression is parsed into a SymPy Boolean expression.
2. `simplify_logic(..., form="dnf")` produces a candidate.
3. Candidate is checked against the original by exhaustive truth table (max 12 variables; beyond that the rule is skipped).
4. A suggestion is shown only if verified AND the textual operator count decreases.
Rules labelled: SELF-AND, SELF-OR, SELF-XOR, DOUBLE-NOT, CONST-PROP, BOOL-SIMPLIFY.
Benefit is reported only as operator-count reduction (a proxy). No area, power, or timing claims are made.
Not covered: arithmetic, comparisons, bit-selects, buses, sequential logic, always blocks.
Applying a suggestion returns new source text; the original is never overwritten. Apply works by exact text match of `assign <sig> = <expr>;`.
