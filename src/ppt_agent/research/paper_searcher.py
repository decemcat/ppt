from __future__ import annotations
from ppt_agent.config import ProxyConfig
from ppt_agent.research.models import Paper


class PaperSearcher:
    def __init__(self, proxy: ProxyConfig | None = None):
        self.proxy = proxy

    def search(self, query: str, max_results: int = 5) -> list[Paper]:
        papers = []
        try:
            papers.extend(self._search_arxiv(query, max_results))
        except ImportError:
            pass
        try:
            papers.extend(self._search_semantic_scholar(query, max_results))
        except ImportError:
            pass
        return papers

    def _search_arxiv(self, query: str, max_results: int) -> list[Paper]:
        import arxiv
        client = arxiv.Client()
        search = arxiv.Search(query=query, max_results=max_results)
        papers = []
        for result in client.results(search):
            papers.append(Paper(
                url=result.entry_id, title=result.title,
                snippet=result.summary[:300], content=result.summary,
                source="paper", arxiv_id=result.get_short_id(),
                authors=[a.name for a in result.authors],
                published=result.published.date() if result.published else None,
                citations=0,
            ))
        return papers

    def _search_semantic_scholar(self, query: str, max_results: int) -> list[Paper]:
        try:
            import requests
            resp = requests.get(
                "https://api.semanticscholar.org/graph/v1/paper/search",
                params={"query": query, "limit": max_results,
                        "fields": "title,url,abstract,citationCount,authors"},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            papers = []
            for item in data.get("data", []):
                papers.append(Paper(
                    url=item.get("url", ""), title=item.get("title", ""),
                    snippet=(item.get("abstract") or "")[:300],
                    content=item.get("abstract") or "",
                    source="paper", arxiv_id=item.get("paperId", ""),
                    citations=item.get("citationCount", 0),
                ))
            return papers
        except Exception:
            return []
