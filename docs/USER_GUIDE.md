# User Guide (Windows)
1. Install Python 3.11+ from python.org (tick "Add to PATH").
2. In the project folder: `python -m venv .venv`, `.venv\Scripts\activate`, `pip install -r requirements.txt`
3. Launch: double-click `scripts\run_windows.bat` (or `python -m app.main`).
4. Sample Projects -> pick one -> Load. It analyzes automatically.
5. Explore Analyze, Circuit View, Optimize RTL (Apply -> Compare), Reports (export).
Optional exe: `python scripts\build_exe.py` -> `dist\RTL-Design-Analyzer-Optimizer\`.
Common errors: "python not found" -> reinstall with PATH ticked; Qt platform plugin error -> `pip install --force-reinstall PySide6`.
