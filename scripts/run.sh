#!/usr/bin/env bash
# Convenience launcher for Linux/macOS development. On Windows, use
# scripts\run_windows.bat instead.
set -e
cd "$(dirname "$0")/.."

if [ ! -d ".venv" ]; then
    echo "Virtual environment not found. Run these commands once first:"
    echo "    python3 -m venv .venv"
    echo "    source .venv/bin/activate"
    echo "    pip install -r requirements.txt"
    exit 1
fi

source .venv/bin/activate
python -m app.main
