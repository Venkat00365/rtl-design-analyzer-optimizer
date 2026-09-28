import os

# Ensure GUI tests can run in headless CI / containers without a display.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
