from pathlib import Path
from ppt_agent.template.analyzer import TemplateInfo, analyze_template


class TestTemplateAnalyzer:
    def test_analyze_minimal(self):
        fixture = Path(__file__).parent / "fixtures" / "minimal_template.pptx"
        info = analyze_template(str(fixture))
        assert isinstance(info, TemplateInfo)
        assert info.slide_width > 0
        assert info.slide_height > 0

    def test_template_missing_file(self):
        import pytest
        with pytest.raises(FileNotFoundError):
            analyze_template("/nonexistent.pptx")
