"""Entry point for the RTL Design Analyzer & Optimizer desktop application."""
import sys

from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("RTL Design Analyzer & Optimizer")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
