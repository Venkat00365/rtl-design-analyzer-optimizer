import glob
import os

import pytest

from app.core.project import AnalysisProject

EXAMPLES_DIR = os.path.join(os.path.dirname(__file__), "..", "examples")


def _example_files():
    return sorted(glob.glob(os.path.join(EXAMPLES_DIR, "*.v")))


@pytest.mark.parametrize("path", _example_files())
def test_bundled_example_parses_without_errors(path):
    src = open(path).read()
    proj = AnalysisProject()
    proj.load(src, os.path.basename(path))
    assert proj.load_errors == [], f"{path} failed to parse: {proj.load_errors}"
    assert len(proj.modules) >= 1
    for mr in proj.modules:
        assert not [i for i in mr.analysis.issues if i.severity == "error"]


def test_exactly_five_bundled_examples_exist():
    assert len(_example_files()) == 5
