from __future__ import annotations

import re

from PySide6.QtCore import Qt, QRect, QSize
from PySide6.QtGui import (
    QColor, QPainter, QSyntaxHighlighter, QTextCharFormat, QFont, QTextCursor
)
from PySide6.QtWidgets import QPlainTextEdit, QWidget, QTextEdit

VERILOG_KEYWORDS = [
    "module", "endmodule", "input", "output", "inout", "wire", "reg", "parameter",
    "assign", "always", "begin", "end", "if", "else", "case", "endcase", "default",
    "posedge", "negedge", "function", "endfunction", "initial", "signed",
]


class VerilogHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.rules = []

        kw_fmt = QTextCharFormat()
        kw_fmt.setForeground(QColor("#6aa4ff"))
        kw_fmt.setFontWeight(QFont.Bold)
        for kw in VERILOG_KEYWORDS:
            self.rules.append((re.compile(rf"\b{kw}\b"), kw_fmt))

        num_fmt = QTextCharFormat()
        num_fmt.setForeground(QColor("#c99b5c"))
        self.rules.append((re.compile(r"\b\d+'[bBhHdD][01xXzZ_a-fA-F]+\b|\b\d+\b"), num_fmt))

        comment_fmt = QTextCharFormat()
        comment_fmt.setForeground(QColor("#6a9955"))
        comment_fmt.setFontItalic(True)
        self.rules.append((re.compile(r"//[^\n]*"), comment_fmt))

        string_fmt = QTextCharFormat()
        string_fmt.setForeground(QColor("#d18f52"))
        self.rules.append((re.compile(r'"[^"\n]*"'), string_fmt))

        op_fmt = QTextCharFormat()
        op_fmt.setForeground(QColor("#e0a0e0"))
        self.rules.append((re.compile(r"[&|~^!=<>+\-*/?:]"), op_fmt))

    def highlightBlock(self, text: str):
        for pattern, fmt in self.rules:
            for m in pattern.finditer(text):
                self.setFormat(m.start(), m.end() - m.start(), fmt)


class LineNumberArea(QWidget):
    def __init__(self, editor: "VerilogEditor"):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)


class VerilogEditor(QPlainTextEdit):
    """A QPlainTextEdit with line numbers and Verilog syntax highlighting."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        font = QFont("Consolas", 11)
        font.setStyleHint(QFont.Monospace)
        self.setFont(font)

        self.line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.update_line_number_area_width(0)
        self.highlight_current_line()

        self.highlighter = VerilogHighlighter(self.document())

    def line_number_area_width(self):
        digits = max(2, len(str(max(1, self.blockCount()))))
        return 12 + self.fontMetrics().horizontalAdvance("9") * digits

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def highlight_current_line(self):
        extra_selections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            line_color = QColor("#23242e")
            selection.format.setBackground(line_color)
            selection.format.setProperty(1, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)
        self.setExtraSelections(extra_selections)

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#16171c"))
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor("#5b5e6b"))
                painter.drawText(0, int(top), self.line_number_area.width() - 6, self.fontMetrics().height(),
                                  Qt.AlignRight, number)
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1
