from __future__ import annotations
import requests
from ppt_agent.config import ProxyConfig
from ppt_agent.research.models import SearchResult
from ppt_agent.research.content_extractor import extract_html


class WebSearcher:
    def __init__(self, proxy: ProxyConfig | None = None):
        self.proxy = proxy
        self._session = self._build_session()

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; PPTAgent/1.0)"})
        if self.proxy and self.proxy.enabled:
            session.proxies = {"http": self.proxy.http, "https": self.proxy.https}
        return session

    def search(self, query: str, num_results: int = 5) -> list[SearchResult]:
        try:
            return self._search_agent_reach(query, num_results)
        except (FileNotFoundError, ImportError, RuntimeError):
            return self._search_direct(query, num_results)

    def _search_agent_reach(self, query: str, num_results: int) -> list[SearchResult]:
        import subprocess, json
        result = subprocess.run(
            ["opencode", "run", "websearch", query],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(f"agent-reach failed: {result.stderr}")
        lines = result.stdout.strip().split("\n")
        results = []
        for line in lines[:num_results]:
            try:
                data = json.loads(line)
                results.append(SearchResult(
                    url=data.get("url", ""), title=data.get("title", ""),
                    snippet=data.get("snippet", ""),
                    content=self.fetch_content(data.get("url", "")),
                    source="web",
                ))
            except json.JSONDecodeError:
                continue
        return results

    def _search_direct(self, query: str, num_results: int) -> list[SearchResult]:
        return []

    def fetch_content(self, url: str) -> str:
        try:
            resp = self._session.get(url, timeout=15)
            resp.raise_for_status()
            return extract_html(resp.text)
        except requests.RequestException:
            return ""
