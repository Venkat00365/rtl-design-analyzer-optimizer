# Architecture
```
Editor text -> parser.VerilogParser -> ParsedModule
                 |-> analyzer.DesignAnalyzer   -> AnalysisResult
                 |-> optimizer.RTLOptimizer    -> suggestions (truth-table verified)
                 |-> visualization.CircuitGraphBuilder -> NetworkX graph -> PNG
core.AnalysisProject orchestrates all; reports.ReportGenerator -> HTML/JSON/CSV
ui.MainWindow (PySide6) is a thin layer over AnalysisProject.
```
