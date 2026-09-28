import pytest

pyside6 = pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication
from app.ui.main_window import MainWindow, NAV_ITEMS

import os

EXAMPLES_DIR = os.path.join(os.path.dirname(__file__), "..", "examples")


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_main_window_creates_all_pages(qapp):
    w = MainWindow()
    assert w.stack.count() == len(NAV_ITEMS)
    assert w.nav_list.count() == len(NAV_ITEMS)
    w.close()


def test_loading_sample_and_analyzing_updates_pages(qapp):
    w = MainWindow()
    src = open(os.path.join(EXAMPLES_DIR, "alu_4bit.v")).read()
    w.editor.setPlainText(src)
    w._run_analysis()
    assert len(w.project.modules) == 1
    assert w.analyze_summary_table.rowCount() > 0
    w.close()


def test_applying_optimization_updates_compare_page(qapp):
    w = MainWindow()
    src = "module m(input wire a, input wire b, output wire y); assign y = a & a; endmodule"
    w.editor.setPlainText(src)
    w._run_analysis()
    mr = w.project.get_module("m")
    assert len(mr.suggestions) == 1
    w._apply_suggestion("m", mr.suggestions[0])
    assert "a;" in w.compare_optimized_editor.toPlainText()
    assert w.project.applied_optimizations
    w.close()


def test_navigation_switches_stack_index(qapp):
    w = MainWindow()
    w._navigate_to("Settings")
    assert w.stack.currentWidget() is w.page_settings
    w.close()
