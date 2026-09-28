# Testing
```
pip install -r requirements.txt
set QT_QPA_PLATFORM=offscreen   (Windows optional; conftest sets it)
python -m pytest tests/ -v
```
Covers parser, analyzer, optimizer, graph builder, reports, all 5 examples, and headless GUI smoke tests.
Not covered: visual appearance, file dialogs (blocking), Windows .exe packaging, Yosys integration (not implemented).
