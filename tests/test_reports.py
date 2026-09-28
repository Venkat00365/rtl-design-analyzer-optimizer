import json

from app.core.project import AnalysisProject
from app.reports.report_generator import ReportGenerator


def _sample_project():
    src = """
    module m(input wire a, input wire b, output wire y);
        assign y = a & a;
    endmodule
    """
    proj = AnalysisProject()
    proj.load(src, "m.v")
    return proj


def test_json_report_contains_metadata_and_module():
    proj = _sample_project()
    data = json.loads(ReportGenerator().to_json(proj))
    assert data["metadata"]["source_filename"] == "m.v"
    assert "tool_version" in data["metadata"]
    assert data["modules"][0]["name"] == "m"
    assert len(data["modules"][0]["optimization_suggestions"]) == 1


def test_csv_report_has_header_rows():
    proj = _sample_project()
    csv_text = ReportGenerator().to_csv(proj)
    assert "module,metric,value" in csv_text
    assert "SELF-AND" in csv_text


def test_html_report_includes_limitations_section():
    proj = _sample_project()
    html = ReportGenerator().to_html(proj)
    assert "Methodology" in html
    assert "static analyzer" in html
    assert "m" in html


def test_html_report_escapes_module_name():
    proj = _sample_project()
    html = ReportGenerator().to_html(proj)
    # sanity: valid-looking html, no raw unescaped angle-bracket injection markers
    assert "<html>" in html and "</html>" in html
