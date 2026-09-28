"""Dark/light Qt stylesheets for the application."""

DARK_QSS = """
QWidget { background-color: #1e1f26; color: #e6e6e6; font-family: "Segoe UI", Arial, sans-serif; font-size: 13px; }
QMainWindow { background-color: #1e1f26; }
#Sidebar { background-color: #16171c; border-right: 1px solid #2b2d38; }
#SidebarButton { text-align: left; padding: 10px 16px; border: none; border-radius: 0px; color: #c7c9d1; font-size: 13px; }
#SidebarButton:hover { background-color: #23242e; }
#SidebarButton:checked { background-color: #2b3a55; color: #7fb3ff; border-left: 3px solid #4d90fe; font-weight: 600; }
#AppTitle { font-size: 16px; font-weight: 700; color: #ffffff; padding: 18px 16px 6px 16px; }
#AppSubtitle { color: #7d8090; font-size: 11px; padding: 0px 16px 14px 16px; }
QPushButton { background-color: #2b3a55; color: #eaf1ff; border: 1px solid #3a4a68; border-radius: 6px; padding: 7px 14px; }
QPushButton:hover { background-color: #35486a; }
QPushButton:pressed { background-color: #24334d; }
QPushButton:disabled { background-color: #2a2b33; color: #6b6d78; border-color: #2a2b33; }
QPushButton#PrimaryButton { background-color: #4d90fe; border: none; font-weight: 600; color: #0b1220; }
QPushButton#PrimaryButton:hover { background-color: #6aa4ff; }
QPushButton#DangerButton { background-color: #a23b3b; border: none; }
QPlainTextEdit, QTextEdit { background-color: #14151b; color: #e6e6e6; border: 1px solid #2b2d38; border-radius: 6px;
    font-family: "Consolas", "Courier New", monospace; font-size: 13px; }
QTableWidget { background-color: #14151b; alternate-background-color: #191a22; gridline-color: #2b2d38; border: 1px solid #2b2d38; border-radius: 6px; }
QHeaderView::section { background-color: #23242e; color: #c7c9d1; padding: 6px; border: none; border-bottom: 1px solid #2b2d38; }
QTabWidget::pane { border: 1px solid #2b2d38; border-radius: 6px; }
QTabBar::tab { background: #23242e; color: #c7c9d1; padding: 8px 16px; border-top-left-radius: 6px; border-top-right-radius: 6px; }
QTabBar::tab:selected { background: #2b3a55; color: #7fb3ff; }
QLabel#PageTitle { font-size: 20px; font-weight: 700; color: #ffffff; padding-bottom: 4px; }
QLabel#PageSubtitle { color: #9497a6; padding-bottom: 12px; }
QLabel#StatCard { background-color: #23242e; border: 1px solid #2b2d38; border-radius: 8px; padding: 14px; }
QLabel#StatValue { font-size: 26px; font-weight: 700; color: #7fb3ff; }
QLabel#StatLabel { color: #9497a6; font-size: 12px; }
QGroupBox { border: 1px solid #2b2d38; border-radius: 8px; margin-top: 10px; padding-top: 10px; font-weight: 600; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 6px; color: #9497a6; }
QStatusBar { background-color: #16171c; color: #9497a6; border-top: 1px solid #2b2d38; }
QComboBox, QLineEdit { background-color: #14151b; border: 1px solid #2b2d38; border-radius: 6px; padding: 4px 8px; }
QListWidget { background-color: transparent; border: none; }
QScrollArea { border: none; }
QToolTip { background-color: #23242e; color: #e6e6e6; border: 1px solid #3a4a68; padding: 4px; }
.warning-badge { color: #f0a020; }
.error-badge { color: #e05555; }
"""

LIGHT_QSS = DARK_QSS.replace("#1e1f26", "#f4f5f8").replace("#16171c", "#e9eaf0") \
    .replace("#e6e6e6", "#1a1a1a").replace("#23242e", "#ffffff") \
    .replace("#14151b", "#ffffff").replace("#2b2d38", "#d5d7e0") \
    .replace("#c7c9d1", "#333640").replace("#9497a6", "#5b5e6b")
