from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap, QAction
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget,
    QListWidgetItem, QStackedWidget, QFileDialog, QTableWidget, QTableWidgetItem,
    QMessageBox, QGroupBox, QScrollArea, QSplitter, QComboBox, QLineEdit, QFrame,
    QHeaderView, QToolBar, QStatusBar, QSizePolicy
)

from app.ui.editor import VerilogEditor
from app.ui.theme import DARK_QSS, LIGHT_QSS
from app.core.project import AnalysisProject
from app.core.version import APP_NAME, APP_VERSION, PARSER_SUBSET_VERSION
from app.reports.report_generator import ReportGenerator
from app.visualization.graph_builder import CircuitGraphBuilder

import sys

if getattr(sys, "frozen", False):  # running from a PyInstaller bundle
    EXAMPLES_DIR = Path(getattr(sys, "_MEIPASS", ".")) / "examples"
else:
    EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "examples"

NAV_ITEMS = [
    "Dashboard", "RTL Editor", "Analyze Design", "Circuit View",
    "Optimize RTL", "Compare Designs", "Reports", "Sample Projects",
    "Settings", "About",
]


def stat_card(value: str, label: str) -> QWidget:
    box = QFrame()
    box.setObjectName("StatCard")
    lay = QVBoxLayout(box)
    v = QLabel(value)
    v.setObjectName("StatValue")
    l = QLabel(label)
    l.setObjectName("StatLabel")
    lay.addWidget(v)
    lay.addWidget(l)
    return box


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.resize(1280, 820)

        self.project = AnalysisProject()
        self.temp_dir = Path(tempfile.mkdtemp(prefix="rtl_analyzer_"))
        self.dark_mode = True

        self._build_ui()
        self.apply_theme()
        self.refresh_all()

    # ------------------------------------------------------------------
    def _build_ui(self):
        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sidebar
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(220)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.setSpacing(0)

        title = QLabel(APP_NAME)
        title.setObjectName("AppTitle")
        title.setWordWrap(True)
        subtitle = QLabel(f"v{APP_VERSION} · Static Verilog Analysis")
        subtitle.setObjectName("AppSubtitle")
        side_layout.addWidget(title)
        side_layout.addWidget(subtitle)

        self.nav_list = QListWidget()
        self.nav_list.setSpacing(2)
        for name in NAV_ITEMS:
            item = QListWidgetItem(name)
            item.setSizeHint(item.sizeHint().expandedTo(item.sizeHint()))
            self.nav_list.addItem(item)
        self.nav_list.setCurrentRow(0)
        self.nav_list.currentRowChanged.connect(self._on_nav_changed)
        self.nav_list.setStyleSheet(
            "QListWidget::item { padding: 10px 16px; color: #c7c9d1; } "
            "QListWidget::item:selected { background-color: #2b3a55; color: #7fb3ff; border-left: 3px solid #4d90fe; }"
        )
        side_layout.addWidget(self.nav_list, 1)

        # Pages
        self.stack = QStackedWidget()
        self.page_dashboard = self._build_dashboard_page()
        self.page_editor = self._build_editor_page()
        self.page_analyze = self._build_analyze_page()
        self.page_circuit = self._build_circuit_page()
        self.page_optimize = self._build_optimize_page()
        self.page_compare = self._build_compare_page()
        self.page_reports = self._build_reports_page()
        self.page_samples = self._build_samples_page()
        self.page_settings = self._build_settings_page()
        self.page_about = self._build_about_page()
        for p in [self.page_dashboard, self.page_editor, self.page_analyze, self.page_circuit,
                  self.page_optimize, self.page_compare, self.page_reports, self.page_samples,
                  self.page_settings, self.page_about]:
            self.stack.addWidget(p)

        root.addWidget(sidebar)
        root.addWidget(self.stack, 1)
        self.setCentralWidget(central)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Ready. No design loaded yet.")

    def _page_container(self, title: str, subtitle: str) -> tuple[QWidget, QVBoxLayout]:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(10)
        t = QLabel(title)
        t.setObjectName("PageTitle")
        s = QLabel(subtitle)
        s.setObjectName("PageSubtitle")
        s.setWordWrap(True)
        lay.addWidget(t)
        lay.addWidget(s)
        return w, lay

    # ------------------------------------------------------------------ Dashboard
    def _build_dashboard_page(self):
        w, lay = self._page_container(
            "Dashboard",
            "Overview of the currently loaded design. Load a sample project or paste RTL in the editor to get started."
        )
        self.dash_stats_row = QHBoxLayout()
        lay.addLayout(self.dash_stats_row)

        self.dash_issues_group = QGroupBox("Recent warnings & errors")
        v = QVBoxLayout(self.dash_issues_group)
        self.dash_issues_table = QTableWidget(0, 3)
        self.dash_issues_table.setHorizontalHeaderLabels(["Severity", "Line", "Message"])
        self.dash_issues_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.dash_issues_table.setEditTriggers(QTableWidget.NoEditTriggers)
        v.addWidget(self.dash_issues_table)
        lay.addWidget(self.dash_issues_group, 1)

        quick_row = QHBoxLayout()
        btn_sample = QPushButton("Load a sample project")
        btn_sample.setObjectName("PrimaryButton")
        btn_sample.clicked.connect(lambda: self._navigate_to("Sample Projects"))
        btn_editor = QPushButton("Open the RTL editor")
        btn_editor.clicked.connect(lambda: self._navigate_to("RTL Editor"))
        quick_row.addWidget(btn_sample)
        quick_row.addWidget(btn_editor)
        quick_row.addStretch()
        lay.addLayout(quick_row)
        return w

    # ------------------------------------------------------------------ Editor
    def _build_editor_page(self):
        w, lay = self._page_container("RTL Editor", "Write, paste, or load Verilog source. Click Analyze when ready.")
        toolbar = QHBoxLayout()
        btn_open = QPushButton("Open .v file...")
        btn_open.clicked.connect(self._open_file)
        btn_save = QPushButton("Save as...")
        btn_save.clicked.connect(self._save_file)
        btn_clear = QPushButton("Clear")
        btn_clear.clicked.connect(lambda: self.editor.setPlainText(""))
        btn_analyze = QPushButton("Analyze Design")
        btn_analyze.setObjectName("PrimaryButton")
        btn_analyze.clicked.connect(self._run_analysis)
        toolbar.addWidget(btn_open)
        toolbar.addWidget(btn_save)
        toolbar.addWidget(btn_clear)
        toolbar.addStretch()
        toolbar.addWidget(btn_analyze)
        lay.addLayout(toolbar)

        self.editor = VerilogEditor()
        self.editor.setPlaceholderText("// Paste or write Verilog here, or load a sample project...")
        lay.addWidget(self.editor, 1)
        self.current_filename_label = QLabel("No file loaded (unsaved buffer)")
        self.current_filename_label.setObjectName("PageSubtitle")
        lay.addWidget(self.current_filename_label)
        return w

    # ------------------------------------------------------------------ Analyze
    def _build_analyze_page(self):
        w, lay = self._page_container("Analyze Design", "Structural summary produced directly from the parsed RTL.")
        self.analyze_module_combo = QComboBox()
        self.analyze_module_combo.currentTextChanged.connect(self._refresh_analyze_page)
        lay.addWidget(self.analyze_module_combo)

        splitter = QSplitter(Qt.Horizontal)
        self.analyze_summary_table = QTableWidget(0, 2)
        self.analyze_summary_table.setHorizontalHeaderLabels(["Metric", "Value"])
        self.analyze_summary_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.analyze_summary_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.analyze_summary_table.verticalHeader().setVisible(False)
        self.analyze_summary_table.setEditTriggers(QTableWidget.NoEditTriggers)
        splitter.addWidget(self.analyze_summary_table)

        self.analyze_issues_table = QTableWidget(0, 3)
        self.analyze_issues_table.setHorizontalHeaderLabels(["Severity", "Line", "Message"])
        self.analyze_issues_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.analyze_issues_table.setEditTriggers(QTableWidget.NoEditTriggers)
        splitter.addWidget(self.analyze_issues_table)
        lay.addWidget(splitter, 1)
        return w

    # ------------------------------------------------------------------ Circuit view
    def _build_circuit_page(self):
        w, lay = self._page_container("Circuit View", "Signal-connectivity graph built directly from the parsed design.")
        row = QHBoxLayout()
        self.circuit_module_combo = QComboBox()
        self.circuit_module_combo.currentTextChanged.connect(self._render_circuit)
        btn_export = QPushButton("Export image...")
        btn_export.clicked.connect(self._export_circuit_image)
        row.addWidget(self.circuit_module_combo)
        row.addStretch()
        row.addWidget(btn_export)
        lay.addLayout(row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.circuit_image_label = QLabel("Load and analyze a design to see its circuit graph here.")
        self.circuit_image_label.setAlignment(Qt.AlignCenter)
        scroll.setWidget(self.circuit_image_label)
        lay.addWidget(scroll, 1)
        return w

    # ------------------------------------------------------------------ Optimize
    def _build_optimize_page(self):
        w, lay = self._page_container(
            "Optimize RTL",
            "Rule-based Boolean simplifications. Every suggestion is verified for exact logical "
            "equivalence before it is shown -- nothing here is a guess."
        )
        self.optimize_module_combo = QComboBox()
        self.optimize_module_combo.currentTextChanged.connect(self._refresh_optimize_page)
        lay.addWidget(self.optimize_module_combo)

        self.optimize_table = QTableWidget(0, 6)
        self.optimize_table.setHorizontalHeaderLabels(
            ["Signal", "Rule", "Original", "Optimized", "Verified", "Apply"])
        self.optimize_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.optimize_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.optimize_table.setEditTriggers(QTableWidget.NoEditTriggers)
        lay.addWidget(self.optimize_table, 1)

        self.optimize_explain_label = QLabel("Select 'Apply' on a suggestion to preview it in Compare Designs.")
        self.optimize_explain_label.setWordWrap(True)
        lay.addWidget(self.optimize_explain_label)
        return w

    # ------------------------------------------------------------------ Compare
    def _build_compare_page(self):
        w, lay = self._page_container("Compare Designs", "Original RTL vs. the optimized version with applied suggestions.")
        splitter = QSplitter(Qt.Horizontal)
        left_box = QVBoxLayout()
        left_wrap = QWidget(); left_wrap.setLayout(left_box)
        left_box.addWidget(QLabel("Original"))
        self.compare_original_editor = VerilogEditor()
        self.compare_original_editor.setReadOnly(True)
        left_box.addWidget(self.compare_original_editor)

        right_box = QVBoxLayout()
        right_wrap = QWidget(); right_wrap.setLayout(right_box)
        right_box.addWidget(QLabel("Optimized (applied suggestions only)"))
        self.compare_optimized_editor = VerilogEditor()
        self.compare_optimized_editor.setReadOnly(True)
        right_box.addWidget(self.compare_optimized_editor)

        splitter.addWidget(left_wrap)
        splitter.addWidget(right_wrap)
        lay.addWidget(splitter, 1)

        self.compare_summary_label = QLabel("No optimizations applied yet. Go to 'Optimize RTL' and click Apply on a suggestion.")
        self.compare_summary_label.setWordWrap(True)
        lay.addWidget(self.compare_summary_label)
        return w

    # ------------------------------------------------------------------ Reports
    def _build_reports_page(self):
        w, lay = self._page_container("Reports", "Export the full analysis as HTML, JSON, or CSV.")
        row = QHBoxLayout()
        btn_html = QPushButton("Export HTML report...")
        btn_html.clicked.connect(lambda: self._export_report("html"))
        btn_json = QPushButton("Export JSON report...")
        btn_json.clicked.connect(lambda: self._export_report("json"))
        btn_csv = QPushButton("Export CSV report...")
        btn_csv.clicked.connect(lambda: self._export_report("csv"))
        row.addWidget(btn_html); row.addWidget(btn_json); row.addWidget(btn_csv); row.addStretch()
        lay.addLayout(row)
        note = QLabel(
            "Every export includes the tool version, parser-subset version, source filename, "
            "an analysis timestamp, and an explicit methodology & limitations section."
        )
        note.setWordWrap(True)
        lay.addWidget(note)
        lay.addStretch()
        return w

    # ------------------------------------------------------------------ Samples
    def _build_samples_page(self):
        w, lay = self._page_container("Sample Projects", "Five original, synthesizable example designs bundled with the app.")
        self.samples_list = QListWidget()
        self._sample_descriptions = {
            "basic_gates.v": "Basic combinational logic — AND/OR/XOR/NAND gates from primary inputs.",
            "alu_4bit.v": "4-bit ALU supporting add, subtract, AND, and OR via a 2-bit opcode.",
            "priority_encoder.v": "4-to-2 priority encoder with a valid output flag.",
            "mux_4to1.v": "4-to-1 multiplexer built from nested 2-to-1 selection logic.",
            "counter_fsm.v": "4-bit synchronous up-counter with synchronous reset and enable.",
        }
        for fname, desc in self._sample_descriptions.items():
            item = QListWidgetItem(f"{fname}\n{desc}")
            item.setData(Qt.UserRole, fname)
            self.samples_list.addItem(item)
        lay.addWidget(self.samples_list, 1)
        btn_load = QPushButton("Load selected sample into editor")
        btn_load.setObjectName("PrimaryButton")
        btn_load.clicked.connect(self._load_selected_sample)
        lay.addWidget(btn_load)
        return w

    # ------------------------------------------------------------------ Settings
    def _build_settings_page(self):
        w, lay = self._page_container("Settings", "Application preferences and optional external tool configuration.")
        theme_group = QGroupBox("Appearance")
        tg_lay = QHBoxLayout(theme_group)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark (default)", "Light"])
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        tg_lay.addWidget(QLabel("Theme:"))
        tg_lay.addWidget(self.theme_combo)
        tg_lay.addStretch()
        lay.addWidget(theme_group)

        yosys_group = QGroupBox("Optional: Yosys synthesis integration")
        yg_lay = QVBoxLayout(yosys_group)
        yg_row = QHBoxLayout()
        self.yosys_path_edit = QLineEdit()
        self.yosys_path_edit.setPlaceholderText("Path to yosys executable (optional)")
        btn_detect = QPushButton("Detect")
        btn_detect.clicked.connect(self._detect_yosys)
        yg_row.addWidget(self.yosys_path_edit)
        yg_row.addWidget(btn_detect)
        self.yosys_status_label = QLabel(
            "Not configured. The app works fully in static-analysis-only mode without Yosys."
        )
        self.yosys_status_label.setWordWrap(True)
        yg_lay.addLayout(yg_row)
        yg_lay.addWidget(self.yosys_status_label)
        lay.addWidget(yosys_group)
        lay.addStretch()
        self._detect_yosys()
        return w

    # ------------------------------------------------------------------ About
    def _build_about_page(self):
        w, lay = self._page_container("About", "")
        text = QLabel(
            f"<h3>{APP_NAME}</h3>"
            f"<p>Version {APP_VERSION} &middot; Parser subset version {PARSER_SUBSET_VERSION}</p>"
            "<p>A desktop tool for static analysis, transparent rule-based optimization suggestions, "
            "and graph-based visualization of a documented, restricted subset of synthesizable Verilog.</p>"
            "<p><b>Technology:</b> Python 3.11+, PySide6, NetworkX, Matplotlib, SymPy (for truth-table "
            "verified Boolean simplification), pytest.</p>"
            "<p><b>Honest limitations:</b> This is not a full Verilog/SystemVerilog compiler and does not "
            "perform simulation or synthesis on its own. It does not report real timing, area, or power. "
            "See docs/RTL_SUPPORTED_FEATURES.md and docs/OPTIMIZATION_METHODOLOGY.md for the exact scope.</p>"
        )
        text.setWordWrap(True)
        text.setTextFormat(Qt.RichText)
        lay.addWidget(text)
        lay.addStretch()
        return w

    # ==================================================================
    # Navigation
    # ==================================================================
    def _on_nav_changed(self, row: int):
        self.stack.setCurrentIndex(row)

    def _navigate_to(self, name: str):
        idx = NAV_ITEMS.index(name)
        self.nav_list.setCurrentRow(idx)

    # ==================================================================
    # File I/O
    # ==================================================================
    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Verilog file", "", "Verilog files (*.v *.sv);;All files (*)")
        if not path:
            return
        try:
            text = Path(path).read_text()
        except Exception as e:
            QMessageBox.critical(self, "Error opening file", str(e))
            return
        self.editor.setPlainText(text)
        self.current_filename_label.setText(f"Loaded: {path}")
        self._navigate_to("RTL Editor")

    def _save_file(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Verilog file", "design.v", "Verilog files (*.v)")
        if not path:
            return
        Path(path).write_text(self.editor.toPlainText())
        self.status.showMessage(f"Saved to {path}", 5000)

    def _load_selected_sample(self):
        item = self.samples_list.currentItem()
        if not item:
            QMessageBox.information(self, "No sample selected", "Select a sample project from the list first.")
            return
        fname = item.data(Qt.UserRole)
        path = EXAMPLES_DIR / fname
        try:
            text = path.read_text()
        except Exception as e:
            QMessageBox.critical(self, "Error loading sample", str(e))
            return
        self.editor.setPlainText(text)
        self.current_filename_label.setText(f"Loaded sample: {fname}")
        self._navigate_to("RTL Editor")
        self._run_analysis()

    # ==================================================================
    # Analysis pipeline
    # ==================================================================
    def _run_analysis(self):
        source = self.editor.toPlainText()
        if not source.strip():
            QMessageBox.warning(self, "Nothing to analyze", "The editor is empty. Paste or load some Verilog first.")
            return
        filename = self.current_filename_label.text().replace("Loaded: ", "").replace("Loaded sample: ", "")
        if filename.startswith("No file"):
            filename = "untitled.v"
        self.project.load(source, filename)
        self.refresh_all()
        if self.project.load_errors:
            QMessageBox.critical(self, "Parse error", "\n".join(self.project.load_errors))
            self._navigate_to("RTL Editor")
        else:
            self.status.showMessage(f"Analyzed {len(self.project.modules)} module(s) from {filename}.", 5000)
            self._navigate_to("Analyze Design")

    def refresh_all(self):
        self._refresh_module_combos()
        self._refresh_dashboard()
        self._refresh_analyze_page()
        self._refresh_optimize_page()
        self._refresh_compare_page()
        if self.circuit_module_combo.count():
            self._render_circuit()

    def _refresh_module_combos(self):
        names = [mr.module.name for mr in self.project.modules]
        for combo in (self.analyze_module_combo, self.circuit_module_combo, self.optimize_module_combo):
            combo.blockSignals(True)
            combo.clear()
            combo.addItems(names)
            combo.blockSignals(False)

    def _current_module_report(self, combo: QComboBox):
        name = combo.currentText()
        return self.project.get_module(name)

    # ---- Dashboard ----
    def _refresh_dashboard(self):
        while self.dash_stats_row.count():
            item = self.dash_stats_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        n_modules = len(self.project.modules)
        total_ports = sum(mr.analysis.num_ports for mr in self.project.modules)
        total_warnings = sum(len(mr.analysis.warnings if hasattr(mr.analysis, "warnings") else []) for mr in self.project.modules)
        total_warnings = sum(len([i for i in mr.analysis.issues if i.severity == "warning"]) for mr in self.project.modules)
        total_suggestions = sum(len(mr.suggestions) for mr in self.project.modules)

        for value, label in [
            (str(n_modules), "Modules loaded"),
            (str(total_ports), "Total ports"),
            (str(total_warnings), "Design warnings"),
            (str(total_suggestions), "Optimization suggestions"),
        ]:
            self.dash_stats_row.addWidget(stat_card(value, label))

        issues = []
        for mr in self.project.modules:
            for i in mr.analysis.issues:
                issues.append(i)
        self.dash_issues_table.setRowCount(len(issues))
        for r, i in enumerate(issues):
            self.dash_issues_table.setItem(r, 0, QTableWidgetItem(i.severity))
            self.dash_issues_table.setItem(r, 1, QTableWidgetItem(str(i.line or "-")))
            self.dash_issues_table.setItem(r, 2, QTableWidgetItem(i.message))

    # ---- Analyze ----
    def _refresh_analyze_page(self):
        mr = self._current_module_report(self.analyze_module_combo)
        self.analyze_summary_table.setRowCount(0)
        self.analyze_issues_table.setRowCount(0)
        if not mr:
            return
        rows = mr.analysis.summary_rows()
        self.analyze_summary_table.setRowCount(len(rows))
        for r, (label, value) in enumerate(rows):
            self.analyze_summary_table.setItem(r, 0, QTableWidgetItem(label))
            self.analyze_summary_table.setItem(r, 1, QTableWidgetItem(value))

        self.analyze_issues_table.setRowCount(len(mr.analysis.issues))
        for r, i in enumerate(mr.analysis.issues):
            self.analyze_issues_table.setItem(r, 0, QTableWidgetItem(i.severity))
            self.analyze_issues_table.setItem(r, 1, QTableWidgetItem(str(i.line or "-")))
            self.analyze_issues_table.setItem(r, 2, QTableWidgetItem(i.message))

    # ---- Circuit ----
    def _render_circuit(self):
        mr = self._current_module_report(self.circuit_module_combo)
        if not mr:
            self.circuit_image_label.setText("Load and analyze a design to see its circuit graph here.")
            self.circuit_image_label.setPixmap(QPixmap())
            return
        gb = CircuitGraphBuilder()
        g = gb.build(mr.module)
        out_path = self.temp_dir / f"{mr.module.name}_graph.png"
        gb.render_png(g, str(out_path), title=mr.module.name)
        self._last_graph_path = out_path
        pix = QPixmap(str(out_path))
        self.circuit_image_label.setPixmap(pix)
        self.circuit_image_label.setText("")

    def _export_circuit_image(self):
        if not hasattr(self, "_last_graph_path") or not self._last_graph_path.exists():
            QMessageBox.information(self, "Nothing to export", "Analyze a design and open Circuit View first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export circuit image", "circuit.png", "PNG images (*.png)")
        if path:
            shutil.copy(self._last_graph_path, path)
            self.status.showMessage(f"Exported circuit image to {path}", 5000)

    # ---- Optimize ----
    def _refresh_optimize_page(self):
        mr = self._current_module_report(self.optimize_module_combo)
        self.optimize_table.setRowCount(0)
        if not mr:
            return
        self.optimize_table.setRowCount(len(mr.suggestions))
        for r, s in enumerate(mr.suggestions):
            self.optimize_table.setItem(r, 0, QTableWidgetItem(s.signal))
            self.optimize_table.setItem(r, 1, QTableWidgetItem(s.rule_name))
            self.optimize_table.setItem(r, 2, QTableWidgetItem(s.original_expr))
            self.optimize_table.setItem(r, 3, QTableWidgetItem(s.optimized_expr))
            self.optimize_table.setItem(r, 4, QTableWidgetItem(s.verified))
            btn = QPushButton("Apply")
            btn.clicked.connect(lambda _checked, mod=mr.module.name, sug=s: self._apply_suggestion(mod, sug))
            self.optimize_table.setCellWidget(r, 5, btn)
        if not mr.suggestions:
            self.optimize_explain_label.setText(
                "No verified Boolean optimization opportunities were found in this module's "
                "continuous assignments."
            )

    def _apply_suggestion(self, module_name: str, suggestion):
        new_source = self.project.apply_optimization(module_name, suggestion)
        self._optimized_source = new_source
        self.optimize_explain_label.setText(
            f"Applied: {suggestion.rule_name} on '{suggestion.signal}' "
            f"({suggestion.original_expr} → {suggestion.optimized_expr}). {suggestion.explanation}"
        )
        self._refresh_compare_page()
        self._navigate_to("Compare Designs")

    # ---- Compare ----
    def _refresh_compare_page(self):
        self.compare_original_editor.setPlainText(self.project.original_source or "")
        optimized = getattr(self, "_optimized_source", None) or self.project.original_source or ""
        self.compare_optimized_editor.setPlainText(optimized)
        applied = self.project.applied_optimizations
        if applied:
            lines = [f"{sig}: {s.rule_name} ({s.original_expr} → {s.optimized_expr})" for sig, s in applied.items()]
            self.compare_summary_label.setText("Applied optimizations:\n" + "\n".join(lines))
        else:
            self.compare_summary_label.setText(
                "No optimizations applied yet. Go to 'Optimize RTL' and click Apply on a suggestion."
            )

    # ---- Reports ----
    def _export_report(self, fmt: str):
        if not self.project.modules:
            QMessageBox.information(self, "Nothing to export", "Analyze a design first.")
            return
        rg = ReportGenerator()
        default_name = f"rtl_report.{fmt}"
        filters = {"html": "HTML files (*.html)", "json": "JSON files (*.json)", "csv": "CSV files (*.csv)"}
        path, _ = QFileDialog.getSaveFileName(self, "Export report", default_name, filters[fmt])
        if not path:
            return
        try:
            if fmt == "html":
                graph_paths = {}
                gb = CircuitGraphBuilder()
                for mr in self.project.modules:
                    g = gb.build(mr.module)
                    img_path = self.temp_dir / f"{mr.module.name}_report_graph.png"
                    gb.render_png(g, str(img_path), title=mr.module.name)
                    graph_paths[mr.module.name] = str(img_path)
                content = rg.to_html(self.project, graph_paths)
            elif fmt == "json":
                content = rg.to_json(self.project)
            else:
                content = rg.to_csv(self.project)
            Path(path).write_text(content)
            self.status.showMessage(f"Report exported to {path}", 5000)
        except Exception as e:
            QMessageBox.critical(self, "Export failed", str(e))

    # ---- Settings ----
    def _detect_yosys(self):
        path = shutil.which("yosys")
        if path:
            self.yosys_path_edit.setText(path)
            self.yosys_status_label.setText(f"Yosys detected at: {path}. Synthesis statistics can be enabled.")
        else:
            self.yosys_status_label.setText(
                "Yosys was not found on this system. The app continues to work fully in "
                "static-analysis-only mode; this is expected and not an error."
            )

    def _on_theme_changed(self, idx: int):
        self.dark_mode = (idx == 0)
        self.apply_theme()

    def apply_theme(self):
        from PySide6.QtWidgets import QApplication
        QApplication.instance().setStyleSheet(DARK_QSS if self.dark_mode else LIGHT_QSS)

    def closeEvent(self, event):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        super().closeEvent(event)
