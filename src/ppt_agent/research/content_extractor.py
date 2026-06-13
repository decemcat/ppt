from __future__ import annotations
import re


def extract_html(html: str) -> str:
    if not html:
        return ""
    try:
        import trafilatura
        result = trafilatura.extract(html, output_format="markdown", include_links=True)
        return result or ""
    except ImportError:
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()
        return text


def extract_readme_summary(readme: str, max_chars: int = 2000) -> str:
    if not readme:
        return ""
    lines = readme.split("\n")
    meaningful = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("[!"):
            continue
        if stripped.startswith("# ") and len(meaningful) > 5:
            break
        meaningful.append(stripped)
    summary = "\n".join(meaningful[:50])
    return summary[:max_chars]
