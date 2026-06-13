from __future__ import annotations
import requests
from ppt_agent.config import ProxyConfig
from ppt_agent.research.models import SearchResult
from ppt_agent.research.content_extractor import extract_html


class WebSearcher:
    def __init__(self, proxy: ProxyConfig | None = None):
        self.proxy = proxy

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; PPTAgent/1.0)"})
        if self.proxy and self.proxy.enabled:
            session.proxies = {"http": self.proxy.http, "https": self.proxy.https}
        return session

    def search(self, query: str, num_results: int = 5) -> list[SearchResult]:
        results: list[SearchResult] = []
        try:
            results = self._duckduckgo_search(query, num_results)
        except Exception:
            pass

        if not results:
            try:
                results = self._duckduckgo_html_search(query, num_results)
            except Exception:
                pass

        return results

    def _duckduckgo_search(self, query: str, max_results: int) -> list[SearchResult]:
        from ddgs import DDGS
        results = []
        with DDGS() as ddgs:
            for item in ddgs.text(query, max_results=max_results):
                results.append(SearchResult(
                    url=item.get("href", ""),
                    title=item.get("title", ""),
                    snippet=item.get("body", ""),
                    source="web",
                ))
        return results

    def _duckduckgo_html_search(self, query: str, num_results: int) -> list[SearchResult]:
        import re
        from urllib.parse import quote_plus
        session = self._build_session()
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        resp = session.get(url, timeout=15)
        resp.raise_for_status()
        results = []
        snippet_matches = re.findall(
            r'<a rel="nofollow" class="result__a" href="([^"]+)"[^>]*>([^<]+)</a>.*?<a class="result__snippet"[^>]*>([^<]+)</a>',
            resp.text, re.DOTALL,
        )
        for href, title, snippet in snippet_matches[:num_results]:
            results.append(SearchResult(
                url=href, title=title.strip(), snippet=snippet.strip(), source="web",
            ))
        return results

    def _fetch_content(self, url: str) -> str:
        try:
            session = self._build_session()
            resp = session.get(url, timeout=15)
            resp.raise_for_status()
            return extract_html(resp.text)
        except requests.RequestException:
            return ""
