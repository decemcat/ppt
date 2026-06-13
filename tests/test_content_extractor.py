from ppt_agent.research.content_extractor import extract_html, extract_readme_summary


class TestContentExtractor:
    def test_extract_html_simple(self):
        html = "<html><body><h1>Title</h1><p>Hello world</p></body></html>"
        result = extract_html(html)
        assert isinstance(result, str)

    def test_extract_html_empty(self):
        assert extract_html("") == ""

    def test_extract_readme_basic(self):
        readme = "# Project\n\nA cool tool.\n\n## Features\n\n- Fast\n- Reliable"
        summary = extract_readme_summary(readme)
        assert len(summary) > 0
