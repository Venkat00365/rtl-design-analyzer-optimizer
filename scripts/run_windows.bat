@echo off
REM One-click launcher for RTL Design Analyzer & Optimizer on Windows.
REM Run this from the project root after completing the setup in
REM docs/USER_GUIDE.md (create the venv and "pip install -r requirements.txt" once).

cd /d "%~dp0\.."

if not exist ".venv\Scripts\activate.bat" (
    echo Virtual environment not found. Run these commands once first:
    echo     python -m venv .venv
    echo     .venv\Scripts\activate
    echo     pip install -r requirements.txt
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
python -m app.main
pause
