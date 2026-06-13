from __future__ import annotations
import requests
import concurrent.futures
from ppt_agent.config import ProxyConfig
from ppt_agent.research.models import SearchResult


class WebSearcher:
    def __init__(self, proxy: ProxyConfig | None = None):
        self.proxy = proxy

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update({"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"})
        if self.proxy and self.proxy.enabled:
            session.proxies = {"http": self.proxy.http, "https": self.proxy.https}
        return session

    def search(self, query: str, num_results: int = 5) -> list[SearchResult]:
        engines = [
            ("DuckDuckGo", self._duckduckgo_search),
            ("Google", self._google_search),
            ("Bing", self._bing_search),
        ]
        results: dict[str, list[SearchResult]] = {}

        def _try(name, fn):
            try:
                results[name] = fn(query, num_results)
            except Exception:
                results[name] = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            futures = {pool.submit(_try, name, fn): name for name, fn in engines}
            done, _not_done = concurrent.futures.wait(futures, timeout=12, return_when=concurrent.futures.FIRST_COMPLETED)
            for f in done:
                _not_done.discard(f)

        for name, _ in engines:
            if name in results and results[name]:
                return results[name][:num_results]
        return []

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

    def _google_search(self, query: str, num_results: int) -> list[SearchResult]:
        from googlesearch import search
        results = []
        for url in search(query, num_results=num_results, advanced=True, timeout=8):
            if hasattr(url, "title"):
                results.append(SearchResult(
                    url=getattr(url, "url", ""),
                    title=getattr(url, "title", ""),
                    snippet=getattr(url, "description", ""),
                    source="web",
                ))
            else:
                results.append(SearchResult(
                    url=str(url), title=str(url), snippet="", source="web",
                ))
        return results

    def _bing_search(self, query: str, num_results: int) -> list[SearchResult]:
        import re
        from urllib.parse import quote_plus
        session = self._build_session()
        url = f"https://www.bing.com/search?q={quote_plus(query)}&count={num_results}&setlang=en"
        resp = session.get(url, timeout=10, headers={"Accept-Language": "en-US,en;q=0.9"})
        resp.raise_for_status()
        results = []
        block_pattern = r'<li class="b_algo"[^>]*>.*?<h2[^>]*>(.*?)</h2>.*?</li>'
        for block_match in re.finditer(block_pattern, resp.text, re.DOTALL):
            block = block_match.group(0)
            href_m = re.search(r'href="(https?://[^"]+)"', block)
            title_m = re.search(r'<h2[^>]*>.*?<a[^>]*>([^<]+)</a>', block, re.DOTALL)
            snippet_m = re.search(r'<p[^>]*>(.*?)</p>', block, re.DOTALL)
            if not href_m:
                continue
            href = href_m.group(1).replace("&amp;", "&")
            title = title_m.group(1).strip() if title_m else href
            snippet = re.sub(r"<[^>]+>", "", snippet_m.group(1)).strip() if snippet_m else ""
            if any(x in href.lower() for x in ("bing.com/dict", "dictionary.", "bing.com/translator")):
                continue
            results.append(SearchResult(
                url=href, title=title, snippet=snippet, source="web",
            ))
            if len(results) >= num_results:
                break
        return results
