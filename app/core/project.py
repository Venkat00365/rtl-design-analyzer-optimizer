"""
project.py
----------
AnalysisProject ties the parser, analyzer, optimizer, and graph builder
together for a single piece of RTL source, and tracks the optional
"optimized" version the user has chosen to preview/apply so the Compare
view has real, consistent data to show. The GUI and the CLI/tests both use
this same object so behavior is guaranteed to be identical.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.parser.verilog_parser import VerilogParser, ParsedModule
from app.analyzer.analyzer import DesignAnalyzer, AnalysisResult
from app.optimizer.optimizer import RTLOptimizer, OptimizationSuggestion
from app.visualization.graph_builder import CircuitGraphBuilder
from app.core.version import APP_NAME, APP_VERSION, PARSER_SUBSET_VERSION


@dataclass
class ModuleReport:
    module: ParsedModule
    analysis: AnalysisResult
    suggestions: list[OptimizationSuggestion] = field(default_factory=list)


@dataclass
class AnalysisProject:
    source_filename: str = "untitled.v"
    original_source: str = ""
    applied_optimizations: dict = field(default_factory=dict)  # signal -> OptimizationSuggestion
    modules: list[ModuleReport] = field(default_factory=list)
    load_errors: list[str] = field(default_factory=list)

    def load(self, source: str, filename: str = "untitled.v"):
        self.original_source = source
        self.source_filename = filename
        self.applied_optimizations = {}
        self.modules = []
        self.load_errors = []

        parser = VerilogParser()
        analyzer = DesignAnalyzer()
        optimizer = RTLOptimizer()
        try:
            parsed_modules = parser.parse(source)
        except Exception as e:
            self.load_errors.append(str(e))
            return

        for mod in parsed_modules:
            analysis = analyzer.analyze(mod)
            suggestions = optimizer.optimize_module(mod)
            self.modules.append(ModuleReport(module=mod, analysis=analysis, suggestions=suggestions))

    # -----------------------------------------------------------------
    def apply_optimization(self, module_name: str, suggestion: OptimizationSuggestion) -> str:
        """Returns a NEW source string with the single suggested replacement
        applied. Does not mutate self.original_source -- the caller decides
        whether/how to keep it (undo is simply 'discard the new string')."""
        new_source = self.original_source.replace(
            f"assign {suggestion.signal} = {suggestion.original_expr};",
            f"assign {suggestion.signal} = {suggestion.optimized_expr};",
            1,
        )
        self.applied_optimizations[suggestion.signal] = suggestion
        return new_source

    def build_graph(self, module_name: str):
        gb = CircuitGraphBuilder()
        for mr in self.modules:
            if mr.module.name == module_name:
                return gb.build(mr.module)
        return None

    def get_module(self, module_name: str) -> ModuleReport | None:
        for mr in self.modules:
            if mr.module.name == module_name:
                return mr
        return None

    def metadata(self) -> dict:
        return {
            "tool_name": APP_NAME,
            "tool_version": APP_VERSION,
            "parser_subset_version": PARSER_SUBSET_VERSION,
            "source_filename": self.source_filename,
            "analysis_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        }
