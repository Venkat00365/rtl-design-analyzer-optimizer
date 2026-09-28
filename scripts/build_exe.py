"""
build_exe.py
------------
Packages the application into a standalone Windows executable using
PyInstaller. Run this ON WINDOWS, from an activated virtual environment
that already has `pip install -r requirements.txt` and PyInstaller
installed (`pip install pyinstaller==6.11.1`).

Usage (from the project root):
    python scripts\\build_exe.py

Output:
    dist\\RTL-Design-Analyzer-Optimizer\\RTL-Design-Analyzer-Optimizer.exe

This script has NOT been executed in this development environment because
it targets Windows specifically and produces a large binary; it is provided
ready to run. See docs/USER_GUIDE.md for the exact verified steps to launch
the app without packaging (python -m app.main), which is confirmed working.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    examples_sep = ";" if sys.platform.startswith("win") else ":"
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "RTL-Design-Analyzer-Optimizer",
        "--windowed",
        "--noconfirm",
        "--collect-all", "numpy",
        "--collect-all", "matplotlib",
        "--add-data", f"{ROOT / 'examples'}{examples_sep}examples",
        str(ROOT / "app" / "main.py"),
    ]
    print("Running:", " ".join(cmd))
    subprocess.check_call(cmd, cwd=str(ROOT))
    print("\nDone. Find the executable under dist/RTL-Design-Analyzer-Optimizer/")


if __name__ == "__main__":
    main()
