# Supported Verilog Subset (parser v1.0)

## Supported
- `module ... endmodule` (multiple modules per file)
- ANSI ports (`input wire [3:0] a`) and non-ANSI ports (separate `input`/`output` lines)
- `wire`, `reg`, `parameter` declarations with `[MSB:LSB]` ranges
- `assign lhs = expr;`
- `always @(posedge clk ...)` (sequential) and `always @(*)` / `@(a or b)` (combinational)
- `if / else if / else`, `case / default / endcase`, blocking and non-blocking assignments
- Operators counted: & | ^ ~ ^~ && || ! + - * / == != < > <= >= << >> ?:

## Not supported (not analyzed, not guessed)
SystemVerilog, `generate`, `function`/`task`, `initial`, module instantiation (no hierarchy), concatenation/replication semantics, memories/arrays, `define`/`include`, multiple always blocks with complex nesting (regex-based extraction).

## Known limitations
- Regex-based parser, not a full grammar; syntax errors are detected only as "no module found" or missing structures. Line-specific syntax diagnostics are limited.
- Non-blocking assignment `<=` is also counted as the `<=` comparison operator, so sequential blocks over-count operators.
- Latch warnings come from textual if-without-else / case-without-default checks; they can produce false positives (e.g. a default assignment before the `if`) and miss nested cases.
- Undriven-signal check is name-presence based.
