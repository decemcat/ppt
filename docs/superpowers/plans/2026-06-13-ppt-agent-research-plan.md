# Research Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the research pipeline that automatically collects knowledge from web, papers, and GitHub, stores it in ChromaDB + knowledge graph, and surfaces it via LLM Wiki.

**Architecture:** ResearchManager orchestrates three searchers (Web, Papers, GitHub). Results are extracted to Markdown, indexed into ChromaDB (semantic search) and NetworkX graph (concept relationships). LLM Wiki provides CLI tree + Flask web UI for browsing. All HTTP requests support proxy configuration for GFW scenarios.

**Tech Stack:** Python 3.11+, chromadb, sentence-transformers, networkx, arxiv, PyGithub, trafilatura, flask, rich, pydantic.

---

## File Structure

```
src/ppt_agent/
├── config.py              # MODIFY — add KnowledgeConfig, ProxyConfig
├── orchestrator.py        # MODIFY — add research phase
└── research/
    ├── __init__.py
    ├── models.py          # SearchResult, Paper, RepoAnalysis, KnowledgeNode, KnowledgeEdge
    ├── web_searcher.py    # WebSearcher — agent-reach + fallback + proxy
    ├── paper_searcher.py  # PaperSearcher — arXiv + Semantic Scholar
    ├── github_analyzer.py # GitHubAnalyzer — PyGithub
    ├── content_extractor.py # HTML→Markdown, README summarizer
    ├── chroma_indexer.py  # ChromaDB wrapper — add/query collections
    ├── knowledge_graph.py # NetworkX wrapper — nodes/edges/save/load
    ├── manager.py         # ResearchManager — orchestrates all above
    ├── wiki.py            # LLM Wiki CLI + Flask server
tests/
├── test_research_models.py
├── test_knowledge_graph.py
├── test_chroma_indexer.py
├── test_content_extractor.py
├── fixtures/
│   ├── sample_article.html
│   └── sample_readme.md
```

---

### Task 1: Research models + config extension

**Files:**
- Create: `src/ppt_agent/research/__init__.py`
- Create: `src/ppt_agent/research/models.py`
- Create: `tests/test_research_models.py`
- Modify: `src/ppt_agent/config.py`

- [ ] **Step 1: Write research models test**

```python
# tests/test_research_models.py
from datetime import datetime, date
from ppt_agent.research.models import (
    SearchResult, Paper, RepoAnalysis,
    KnowledgeNode, KnowledgeEdge,
)


class TestSearchResult:
    def test_web_result(self):
        r = SearchResult(url="https://example.com", title="Test", snippet="desc", content="# Hello", source="web")
        assert r.source == "web"
        assert r.collected_at is not None

    def test_paper_result(self):
        p = Paper(url="https://arxiv.org/abs/1234", title="Paper", snippet="abstract", content="full", source="paper",
                  arxiv_id="1234", authors=["Author A"], published=date(2025, 1, 1))
        assert p.arxiv_id == "1234"
        assert p.citations == 0

    def test_repo_analysis(self):
        r = RepoAnalysis(repo="user/proj", description="desc", stars=42, topics=["ai"], readme_summary="summary",
                         last_commit=datetime.now())
        assert r.repo == "user/proj"


class TestKnowledgeGraph:
    def test_node_creation(self):
        n = KnowledgeNode(id="k8s", label="Kubernetes", type="concept", summary="Container orchestration", sources=[])
        assert n.type == "concept"

    def test_edge_creation(self):
        e = KnowledgeEdge(source_id="k8s", target_id="docker", relation="extends")
        assert e.relation == "extends"
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/python -m pytest tests/test_research_models.py -v`
Expected: ModuleNotFoundError

- [ ] **Step 3: Write research models**

```python
# src/ppt_agent/research/__init__.py
```

```python
# src/ppt_agent/research/models.py
from __future__ import annotations
from datetime import datetime, date
from typing import Literal
from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    url: str
    title: str
    snippet: str
    content: str
    source: Literal["web", "paper", "github"]
    collected_at: datetime = Field(default_factory=datetime.now)
    metadata: dict = Field(default_factory=dict)


class Paper(SearchResult):
    arxiv_id: str
    authors: list[str] = Field(default_factory=list)
    published: date | None = None
    citations: int = 0


class RepoAnalysis(BaseModel):
    repo: str
    description: str
    stars: int = 0
    topics: list[str] = Field(default_factory=list)
    readme_summary: str = ""
    last_commit: datetime | None = None


class KnowledgeNode(BaseModel):
    id: str
    label: str
    type: Literal["concept", "paper", "project", "person", "tool"]
    summary: str = ""
    sources: list[str] = Field(default_factory=list)


class KnowledgeEdge(BaseModel):
    source_id: str
    target_id: str
    relation: str
```

- [ ] **Step 4: Extend config with KnowledgeConfig and ProxyConfig**

```python
# Add to src/ppt_agent/config.py
class KnowledgeConfig(BaseModel):
    max_age_days: int = 180
    auto_summarize: bool = True
    chroma_path: str = ""
    graph_path: str = ""

    @property
    def resolved_chroma_path(self) -> str:
        return self.chroma_path or str(Path.home() / ".ppt-agent" / "knowledge" / "chroma")

    @property
    def resolved_graph_path(self) -> str:
        return self.graph_path or str(Path.home() / ".ppt-agent" / "knowledge" / "graph" / "graph.json")


class ProxyConfig(BaseModel):
    enabled: bool = True
    http: str = "http://127.0.0.1:7890"
    https: str = "http://127.0.0.1:7890"
```

Add to Config class:
```python
class Config(BaseModel):
    template_path: str = ""
    llm: LLMConfig = Field(default_factory=LLMConfig)
    knowledge: KnowledgeConfig = Field(default_factory=KnowledgeConfig)
    proxy: ProxyConfig = Field(default_factory=ProxyConfig)
```

- [ ] **Step 5: Update imports in config.py**

```python
from __future__ import annotations
from pathlib import Path
import yaml
from pydantic import BaseModel, Field
```

- [ ] **Step 6: Run tests**

Run: `.venv/bin/python -m pytest tests/test_research_models.py tests/test_config.py -v`
Expected: all pass

- [ ] **Step 7: Commit**

```
git add src/ppt_agent/research/ tests/test_research_models.py src/ppt_agent/config.py
git commit -m "feat: add research models and config extension"
```

---

### Task 2: Content extractor

**Files:**
- Create: `src/ppt_agent/research/content_extractor.py`
- Create: `tests/test_content_extractor.py`
- Create: `tests/fixtures/sample_article.html`

- [ ] **Step 1: Write content extractor test**

```python
# tests/test_content_extractor.py
from ppt_agent.research.content_extractor import extract_html, extract_readme_summary


class TestContentExtractor:
    def test_extract_html_simple(self):
        html = "<html><body><h1>Title</h1><p>Hello world</p></body></html>"
        result = extract_html(html)
        assert "Title" in result
        assert "Hello world" in result

    def test_extract_html_empty(self):
        assert extract_html("") == ""

    def test_extract_readme_basic(self):
        readme = "# Project\n\nA cool tool.\n\n## Features\n\n- Fast\n- Reliable"
        summary = extract_readme_summary(readme)
        assert len(summary) > 0
        assert "Project" not in summary  # Should strip markdown headers meaningfully
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/python -m pytest tests/test_content_extractor.py -v`
Expected: ModuleNotFoundError

- [ ] **Step 3: Write content extractor**

```python
# src/ppt_agent/research/content_extractor.py
from __future__ import annotations
import re


def extract_html(html: str) -> str:
    """Convert HTML to Markdown text using trafilatura."""
    if not html:
        return ""
    try:
        import trafilatura
        result = trafilatura.extract(html, output_format="markdown", include_links=True)
        return result or ""
    except ImportError:
        # Fallback: basic tag stripping
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()
        return text


def extract_readme_summary(readme: str, max_chars: int = 2000) -> str:
    """Extract a concise summary from README markdown.

    Takes the first meaningful section, excluding badges and project name boilerplate.
    """
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
```

- [ ] **Step 4: Create test fixture**

```python
# scripts/generate_fixtures.py — run once
fixture_html = """<html><head><title>Test Article</title></head><body>
<article>
<h1>Kubernetes for AI Workloads</h1>
<p>This article explores running AI training on Kubernetes.</p>
<h2>Key Considerations</h2>
<ul>
<li>GPU scheduling with node labels</li>
<li>Distributed training with PyTorch</li>
</ul>
</article></body></html>"""
with open("tests/fixtures/sample_article.html", "w") as f:
    f.write(fixture_html)
```

- [ ] **Step 5: Run tests**

Run: `.venv/bin/python -m pytest tests/test_content_extractor.py -v`
Expected: all pass

- [ ] **Step 6: Commit**

```
git add src/ppt_agent/research/content_extractor.py tests/test_content_extractor.py tests/fixtures/sample_article.html
git commit -m "feat: add content extractor (HTML→Markdown, README summary)"
```

---

### Task 3: Web searcher

**Files:**
- Create: `src/ppt_agent/research/web_searcher.py`

- [ ] **Step 1: Write web searcher**

```python
# src/ppt_agent/research/web_searcher.py
from __future__ import annotations
import requests
from urllib.parse import quote_plus
from ppt_agent.config import ProxyConfig
from ppt_agent.research.models import SearchResult
from ppt_agent.research.content_extractor import extract_html


class WebSearcher:
    def __init__(self, proxy: ProxyConfig | None = None):
        self.proxy = proxy
        self._session = self._build_session()

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; PPTAgent/1.0)"
        })
        if self.proxy and self.proxy.enabled:
            session.proxies = {
                "http": self.proxy.http,
                "https": self.proxy.https,
            }
        return session

    def search(self, query: str, num_results: int = 5) -> list[SearchResult]:
        """Search the web for a query.

        Uses agent-reach CLI if available, falls back to direct search.
        """
        try:
            return self._search_agent_reach(query, num_results)
        except (FileNotFoundError, ImportError):
            return self._search_direct(query, num_results)

    def _search_agent_reach(self, query: str, num_results: int) -> list[SearchResult]:
        """Use agent-reach CLI for web search."""
        import subprocess
        import json
        result = subprocess.run(
            ["opencode", "run", "websearch", query],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(f"agent-reach failed: {result.stderr}")
        # Parse agent-reach output — expects JSONL
        lines = result.stdout.strip().split("\n")
        results = []
        for line in lines[:num_results]:
            try:
                data = json.loads(line)
                results.append(SearchResult(
                    url=data.get("url", ""),
                    title=data.get("title", ""),
                    snippet=data.get("snippet", ""),
                    content=self.fetch_content(data.get("url", "")),
                    source="web",
                ))
            except json.JSONDecodeError:
                continue
        return results

    def _search_direct(self, query: str, num_results: int) -> list[SearchResult]:
        """Fallback: use a direct web search approach.

        For now returns empty — specific search API keys would go here.
        """
        return []

    def fetch_content(self, url: str) -> str:
        """Fetch and extract content from a URL."""
        try:
            resp = self._session.get(url, timeout=15)
            resp.raise_for_status()
            return extract_html(resp.text)
        except requests.RequestException:
            return ""
```

- [ ] **Step 2: Verify import works**

Run: `.venv/bin/python -c "from ppt_agent.research.web_searcher import WebSearcher; print('OK')"`
Expected: "OK"

- [ ] **Step 3: Commit**

```
git add src/ppt_agent/research/web_searcher.py
git commit -m "feat: add web searcher with proxy and agent-reach support"
```

---

### Task 4: Paper searcher

**Files:**
- Create: `src/ppt_agent/research/paper_searcher.py`

- [ ] **Step 1: Write paper searcher**

```python
# src/ppt_agent/research/paper_searcher.py
from __future__ import annotations
from datetime import datetime
from ppt_agent.config import ProxyConfig
from ppt_agent.research.models import Paper


class PaperSearcher:
    def __init__(self, proxy: ProxyConfig | None = None):
        self.proxy = proxy

    def search(self, query: str, max_results: int = 5) -> list[Paper]:
        """Search for papers across arXiv and Semantic Scholar."""
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
                url=result.entry_id,
                title=result.title,
                snippet=result.summary[:300],
                content=result.summary,
                source="paper",
                arxiv_id=result.get_short_id(),
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
                params={"query": query, "limit": max_results, "fields": "title,url,abstract,citationCount,authors"},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            papers = []
            for item in data.get("data", []):
                papers.append(Paper(
                    url=item.get("url", ""),
                    title=item.get("title", ""),
                    snippet=(item.get("abstract") or "")[:300],
                    content=item.get("abstract") or "",
                    source="paper",
                    arxiv_id=item.get("paperId", ""),
                    citations=item.get("citationCount", 0),
                ))
            return papers
        except Exception:
            return []
```

- [ ] **Step 2: Verify import works**

Run: `.venv/bin/python -c "from ppt_agent.research.paper_searcher import PaperSearcher; print('OK')"`
Expected: "OK"

- [ ] **Step 3: Commit**

```
git add src/ppt_agent/research/paper_searcher.py
git commit -m "feat: add paper searcher (arXiv + Semantic Scholar)"
```

---

### Task 5: GitHub analyzer

**Files:**
- Create: `src/ppt_agent/research/github_analyzer.py`

- [ ] **Step 1: Write GitHub analyzer**

```python
# src/ppt_agent/research/github_analyzer.py
from __future__ import annotations
from datetime import datetime
from ppt_agent.research.models import RepoAnalysis
from ppt_agent.research.content_extractor import extract_readme_summary


class GitHubAnalyzer:
    def __init__(self, token: str = ""):
        self.token = token

    def search(self, query: str, max_results: int = 5) -> list[RepoAnalysis]:
        """Search GitHub repositories."""
        try:
            return self._search_pygithub(query, max_results)
        except ImportError:
            return self._search_gh_cli(query, max_results)

    def _search_pygithub(self, query: str, max_results: int) -> list[RepoAnalysis]:
        from github import Github
        g = Github(self.token) if self.token else Github()
        repos = g.search_repositories(query, sort="stars", order="desc")
        results = []
        for repo in repos[:max_results]:
            readme_text = ""
            try:
                readme_text = repo.get_readme().decoded_content.decode("utf-8")
            except Exception:
                pass
            results.append(RepoAnalysis(
                repo=repo.full_name,
                description=repo.description or "",
                stars=repo.stargazers_count,
                topics=repo.get_topics(),
                readme_summary=extract_readme_summary(readme_text),
                last_commit=repo.updated_at if repo.updated_at else datetime.now(),
            ))
        return results

    def _search_gh_cli(self, query: str, max_results: int) -> list[RepoAnalysis]:
        """Fallback using gh CLI."""
        import subprocess, json
        result = subprocess.run(
            ["gh", "search", "repos", query, "--json", "name,owner,description,stargazersCount", f"--limit={max_results}"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return []
        try:
            data = json.loads(result.stdout)
            return [RepoAnalysis(
                repo=f"{item['owner']['login']}/{item['name']}",
                description=item.get("description", ""),
                stars=item.get("stargazersCount", 0),
            ) for item in data]
        except (json.JSONDecodeError, KeyError):
            return []

    def analyze_repo(self, repo_full_name: str) -> RepoAnalysis | None:
        """Get detailed analysis for a specific repo."""
        results = self._search_pygithub(repo_full_name, 1)
        return results[0] if results else None
```

- [ ] **Step 2: Verify import works**

Run: `.venv/bin/python -c "from ppt_agent.research.github_analyzer import GitHubAnalyzer; print('OK')"`
Expected: "OK"

- [ ] **Step 3: Commit**

```
git add src/ppt_agent/research/github_analyzer.py
git commit -m "feat: add GitHub analyzer (PyGithub + gh CLI fallback)"
```

---

### Task 6: Knowledge graph (NetworkX)

**Files:**
- Create: `src/ppt_agent/research/knowledge_graph.py`
- Create: `tests/test_knowledge_graph.py`

- [ ] **Step 1: Write knowledge graph test**

```python
# tests/test_knowledge_graph.py
from pathlib import Path
from ppt_agent.research.knowledge_graph import KnowledgeGraph
from ppt_agent.research.models import KnowledgeNode, KnowledgeEdge


class TestKnowledgeGraph:
    def test_add_node(self):
        kg = KnowledgeGraph()
        n = KnowledgeNode(id="k8s", label="Kubernetes", type="concept", summary="Orch")
        kg.add_node(n)
        assert kg.has_node("k8s")

    def test_add_edge(self):
        kg = KnowledgeGraph()
        kg.add_node(KnowledgeNode(id="a", label="A", type="concept"))
        kg.add_node(KnowledgeNode(id="b", label="B", type="concept"))
        kg.add_edge(KnowledgeEdge(source_id="a", target_id="b", relation="related"))
        assert kg.has_edge("a", "b")

    def test_find_path(self):
        kg = KnowledgeGraph()
        kg.add_node(KnowledgeNode(id="a", label="A", type="concept"))
        kg.add_node(KnowledgeNode(id="b", label="B", type="concept"))
        kg.add_node(KnowledgeNode(id="c", label="C", type="concept"))
        kg.add_edge(KnowledgeEdge(source_id="a", target_id="b", relation="related"))
        kg.add_edge(KnowledgeEdge(source_id="b", target_id="c", relation="related"))
        path = kg.find_path("a", "c")
        assert len(path) == 3

    def test_save_and_load(self, tmp_path):
        kg = KnowledgeGraph()
        kg.add_node(KnowledgeNode(id="x", label="X", type="tool"))
        path = str(tmp_path / "graph.json")
        kg.save(path)
        kg2 = KnowledgeGraph.load(path)
        assert kg2.has_node("x")

    def test_search_nodes(self):
        kg = KnowledgeGraph()
        kg.add_node(KnowledgeNode(id="k8s", label="Kubernetes", type="concept", summary="Container orchestration"))
        kg.add_node(KnowledgeNode(id="docker", label="Docker", type="tool"))
        results = kg.search_nodes("container")
        assert len(results) >= 1
        assert results[0].id == "k8s"
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/python -m pytest tests/test_knowledge_graph.py -v`
Expected: ModuleNotFoundError

- [ ] **Step 3: Write knowledge graph**

```python
# src/ppt_agent/research/knowledge_graph.py
from __future__ import annotations
from pathlib import Path
import networkx as nx
from ppt_agent.research.models import KnowledgeNode, KnowledgeEdge


class KnowledgeGraph:
    def __init__(self):
        self._graph = nx.DiGraph()

    def add_node(self, node: KnowledgeNode):
        self._graph.add_node(node.id, label=node.label, type=node.type,
                              summary=node.summary, sources=node.sources)

    def add_edge(self, edge: KnowledgeEdge):
        self._graph.add_edge(edge.source_id, edge.target_id, relation=edge.relation)

    def has_node(self, node_id: str) -> bool:
        return self._graph.has_node(node_id)

    def has_edge(self, source_id: str, target_id: str) -> bool:
        return self._graph.has_edge(source_id, target_id)

    def get_node(self, node_id: str) -> KnowledgeNode | None:
        if not self._graph.has_node(node_id):
            return None
        data = self._graph.nodes[node_id]
        return KnowledgeNode(
            id=node_id,
            label=data.get("label", node_id),
            type=data.get("type", "concept"),
            summary=data.get("summary", ""),
            sources=data.get("sources", []),
        )

    def find_path(self, source_id: str, target_id: str) -> list[str]:
        """Find shortest path between two nodes."""
        try:
            return nx.shortest_path(self._graph, source_id, target_id)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []

    def get_related(self, node_id: str, max_depth: int = 2) -> list[KnowledgeNode]:
        """Get nodes within max_depth of the given node."""
        if not self._graph.has_node(node_id):
            return []
        related = set()
        for node in nx.dfs_preorder_nodes(self._graph, source=node_id, depth_limit=max_depth):
            related.add(node)
        for node in nx.dfs_preorder_nodes(self._graph.reverse(), source=node_id, depth_limit=max_depth):
            related.add(node)
        return [self.get_node(n) for n in related if n != node_id and self.get_node(n) is not None]

    def search_nodes(self, query: str) -> list[KnowledgeNode]:
        """Simple text search on node labels and summaries."""
        query_lower = query.lower()
        results = []
        for node_id in self._graph.nodes:
            data = self._graph.nodes[node_id]
            label = data.get("label", "").lower()
            summary = data.get("summary", "").lower()
            if query_lower in label or query_lower in summary:
                results.append(self.get_node(node_id))
        return results

    def save(self, path: str):
        """Serialize graph to JSON."""
        from networkx.readwrite import json_graph
        data = json_graph.node_link_data(self._graph)
        import json
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: str) -> KnowledgeGraph:
        """Deserialize graph from JSON."""
        from networkx.readwrite import json_graph
        import json
        kg = cls()
        if Path(path).exists():
            with open(path) as f:
                data = json.load(f)
            kg._graph = json_graph.node_link_graph(data, directed=True)
        return kg

    def count(self) -> dict:
        return {"nodes": self._graph.number_of_nodes(), "edges": self._graph.number_of_edges()}

    def auto_index(self, results: list[SearchResult]):
        """Automatically index search results into the knowledge graph."""
        from ppt_agent.research.models import SearchResult
        for r in results:
            # Create node from result title
            node_id = r.url.split("/")[-1][:50] or r.title[:50]
            source_type = {"web": "concept", "paper": "paper", "github": "project"}.get(r.source, "concept")
            node = KnowledgeNode(
                id=node_id,
                label=r.title[:100],
                type=source_type,
                summary=r.snippet[:500],
                sources=[r.url],
            )
            self.add_node(node)
```

Note: add `from ppt_agent.research.models import SearchResult` import at the top of the file.

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/test_knowledge_graph.py -v`
Expected: all pass

- [ ] **Step 5: Commit**

```
git add src/ppt_agent/research/knowledge_graph.py tests/test_knowledge_graph.py
git commit -m "feat: add knowledge graph with NetworkX"
```

---

### Task 7: ChromaDB indexer

**Files:**
- Create: `src/ppt_agent/research/chroma_indexer.py`
- Create: `tests/test_chroma_indexer.py`

- [ ] **Step 1: Write ChromaDB indexer test**

```python
# tests/test_chroma_indexer.py
from ppt_agent.research.chroma_indexer import ChromaIndexer


class TestChromaIndexer:
    def test_init(self, tmp_path):
        indexer = ChromaIndexer(persist_dir=str(tmp_path))
        assert indexer is not None

    def test_add_and_search(self, tmp_path):
        indexer = ChromaIndexer(persist_dir=str(tmp_path))
        indexer.add_document(id="doc1", text="Kubernetes for AI training", metadata={"source": "web"})
        results = indexer.search("AI training", top_k=5)
        assert len(results) > 0

    def test_search_by_source(self, tmp_path):
        indexer = ChromaIndexer(persist_dir=str(tmp_path))
        indexer.add_document(id="w1", text="Web article about ML", metadata={"source": "web"})
        indexer.add_document(id="p1", text="Paper about deep learning", metadata={"source": "paper"})
        results = indexer.search("ML", top_k=5, source_filter="web")
        assert all(r["metadata"].get("source") == "web" for r in results)
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/python -m pytest tests/test_chroma_indexer.py -v`
Expected: ModuleNotFoundError

- [ ] **Step 3: Write ChromaDB indexer**

```python
# src/ppt_agent/research/chroma_indexer.py
from __future__ import annotations
from pathlib import Path
import chromadb
from chromadb.config import Settings


class ChromaIndexer:
    def __init__(self, persist_dir: str = ""):
        if not persist_dir:
            persist_dir = str(Path.home() / ".ppt-agent" / "knowledge" / "chroma")
        self._client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        self._collections = {}

    def _get_collection(self, name: str):
        if name not in self._collections:
            try:
                self._collections[name] = self._client.get_collection(name)
            except Exception:
                self._collections[name] = self._client.create_collection(name)
        return self._collections[name]

    def add_document(self, id: str, text: str, metadata: dict | None = None, collection: str = "knowledge"):
        col = self._get_collection(collection)
        col.add(
            documents=[text],
            metadatas=[metadata or {}],
            ids=[id],
        )

    def add_documents(self, documents: list[dict], collection: str = "knowledge"):
        """Add multiple documents. Each dict: {id, text, metadata}."""
        col = self._get_collection(collection)
        col.add(
            documents=[d["text"] for d in documents],
            metadatas=[d.get("metadata", {}) for d in documents],
            ids=[d["id"] for d in documents],
        )

    def search(self, query: str, top_k: int = 10, source_filter: str | None = None, collection: str = "knowledge") -> list[dict]:
        col = self._get_collection(collection)
        where = {"source": source_filter} if source_filter else None
        results = col.query(query_texts=[query], n_results=top_k, where=where)
        output = []
        for i in range(len(results["ids"][0])):
            output.append({
                "id": results["ids"][0][i],
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "distance": results["distances"][0][i] if results["distances"] else 0,
            })
        return output

    def count(self, collection: str = "knowledge") -> int:
        col = self._get_collection(collection)
        return col.count()
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/test_chroma_indexer.py -v`
Expected: all pass

- [ ] **Step 5: Commit**

```
git add src/ppt_agent/research/chroma_indexer.py tests/test_chroma_indexer.py
git commit -m "feat: add ChromaDB vector indexer"
```

---

### Task 8: LLM Wiki

**Files:**
- Create: `src/ppt_agent/research/wiki.py`

- [ ] **Step 1: Write wiki module**

```python
# src/ppt_agent/research/wiki.py
from __future__ import annotations
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from rich.prompt import Prompt
from rich.panel import Panel

from ppt_agent.research.knowledge_graph import KnowledgeGraph
from ppt_agent.research.chroma_indexer import ChromaIndexer

console = Console()


class WikiCLI:
    """CLI-based LLM Wiki browser."""

    def __init__(self, graph: KnowledgeGraph, indexer: ChromaIndexer):
        self.graph = graph
        self.indexer = indexer

    def run(self):
        """Interactive CLI wiki browser."""
        console.print(Panel("[bold]LLM Wiki Browser[/bold]\n"
                           "Commands: search <query> | graph <node> | stats | tree | help | quit", style="blue"))
        while True:
            cmd = Prompt.ask("[bold wiki]").strip()
            if cmd == "quit":
                break
            elif cmd == "help":
                console.print("  search <q> — semantic search\n  graph <id> — show related nodes\n  stats — graph stats\n  tree — show all nodes")
            elif cmd.startswith("search "):
                self._handle_search(cmd[7:])
            elif cmd.startswith("graph "):
                self._handle_graph(cmd[6:])
            elif cmd == "stats":
                self._handle_stats()
            elif cmd == "tree":
                self._handle_tree()
            else:
                console.print("[yellow]Unknown command. Type help.[/yellow]")

    def _handle_search(self, query: str):
        results = self.indexer.search(query, top_k=5)
        if not results:
            console.print("[yellow]No results.[/yellow]")
            return
        table = Table(title=f"Search: {query}")
        table.add_column("ID", style="dim")
        table.add_column("Snippet")
        table.add_column("Source")
        for r in results:
            table.add_row(r["id"][:20], r["text"][:80], r["metadata"].get("source", "?"))
        console.print(table)

    def _handle_graph(self, node_id: str):
        node = self.graph.get_node(node_id)
        if not node:
            console.print(f"[yellow]Node '{node_id}' not found.[/yellow]")
            return
        related = self.graph.get_related(node_id)
        tree = Tree(f"[bold]{node.label}[/bold] ({node.type})")
        for r in related:
            tree.add(f"{r.label} ({r.type})")
        console.print(tree)

    def _handle_stats(self):
        stats = self.graph.count()
        chroma_count = self.indexer.count()
        console.print(f"[green]Knowledge Graph:[/green] {stats['nodes']} nodes, {stats['edges']} edges")
        console.print(f"[green]Vector Store:[/green] {chroma_count} documents")

    def _handle_tree(self):
        tree = Tree("[bold]Knowledge Graph[/bold]")
        # Simple: show all nodes grouped by type
        nodes = {}
        # Access graph's internal networkx directly for listing
        for node_id in self.graph._graph.nodes:
            data = self.graph._graph.nodes[node_id]
            ntype = data.get("type", "concept")
            if ntype not in nodes:
                nodes[ntype] = Tree(f"[blue]{ntype}[/blue]")
            nodes[ntype].add(f"{data.get('label', node_id)} [dim]{node_id}[/dim]")
        for ntype, subtree in nodes.items():
            tree.add(subtree)
        console.print(tree)


class WikiServer:
    """Flask-based HTML Wiki server."""

    def __init__(self, graph: KnowledgeGraph, indexer: ChromaIndexer, host: str = "127.0.0.1", port: int = 8765):
        self.graph = graph
        self.indexer = indexer
        self.host = host
        self.port = port

    def run(self):
        """Start the Flask wiki server."""
        try:
            from flask import Flask, jsonify, request, render_template_string
        except ImportError:
            console.print("[red]Flask not installed. Run: pip install flask[/red]")
            return

        app = Flask(__name__)

        @app.route("/")
        def index():
            stats = self.graph.count()
            html = f"""<html><head><title>LLM Wiki</title>
            <style>body{{font-family:sans-serif;max-width:900px;margin:auto;padding:20px}}
            .node{{border:1px solid #ddd;padding:10px;margin:5px;border-radius:5px}}
            .node:hover{{background:#f5f5f5}}</style></head>
            <body><h1>LLM Wiki</h1>
            <form action="/search" method="get">
            <input name="q" size="40" placeholder="Search knowledge base...">
            <button>Search</button>
            </form>
            <p>{stats['nodes']} nodes, {stats['edges']} edges</p>
            <h2>Graph Visualization</h2>
            <div id="graph" style="width:100%;height:500px;border:1px solid #ccc"></div>
            <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
            <script>
            fetch('/api/graph').then(r=>r.json()).then(data=>{{
                var nodes=new vis.DataSet(data.nodes);
                var edges=new vis.DataSet(data.edges);
                var container=document.getElementById('graph');
                new vis.Network(container,{{nodes:nodes,edges:edges}},{{physics:false}});
            }});
            </script></body></html>"""
            return render_template_string(html)

        @app.route("/search")
        def search():
            q = request.args.get("q", "")
            results = self.indexer.search(q, top_k=10)
            items = "".join(f'<div class="node"><b>{r["id"]}</b><p>{r["text"][:200]}</p><small>source: {r["metadata"].get("source","?")}</small></div>'
                          for r in results)
            return f"<html><body><h1>Search: {q}</h1>{items}<a href='/'>Back</a></body></html>"

        @app.route("/api/graph")
        def api_graph():
            nodes = []
            edges = []
            for nid in self.graph._graph.nodes:
                data = self.graph._graph.nodes[nid]
                nodes.append({"id": nid, "label": data.get("label", nid), "group": data.get("type", "concept")})
            for u, v, d in self.graph._graph.edges(data=True):
                edges.append({"from": u, "to": v, "label": d.get("relation", "")})
            return jsonify({"nodes": nodes, "edges": edges})

        console.print(f"[green]Wiki server started at http://{self.host}:{self.port}[/green]")
        app.run(host=self.host, port=self.port, debug=False)
```

- [ ] **Step 2: Verify import works**

Run: `.venv/bin/python -c "from ppt_agent.research.wiki import WikiCLI, WikiServer; print('OK')"`
Expected: "OK"

- [ ] **Step 3: Commit**

```
git add src/ppt_agent/research/wiki.py
git commit -m "feat: add LLM Wiki (CLI browser + Flask web server)"
```

---

### Task 9: ResearchManager (wiring)

**Files:**
- Create: `src/ppt_agent/research/manager.py`

- [ ] **Step 1: Write ResearchManager**

```python
# src/ppt_agent/research/manager.py
from __future__ import annotations
from datetime import datetime, timedelta
from ppt_agent.config import Config
from ppt_agent.research.models import SearchResult
from ppt_agent.research.web_searcher import WebSearcher
from ppt_agent.research.paper_searcher import PaperSearcher
from ppt_agent.research.github_analyzer import GitHubAnalyzer
from ppt_agent.research.chroma_indexer import ChromaIndexer
from ppt_agent.research.knowledge_graph import KnowledgeGraph
from ppt_agent.research.wiki import WikiCLI, WikiServer


class ResearchManager:
    """Orchestrates the full research pipeline."""

    def __init__(self, config: Config):
        self.config = config
        self.web = WebSearcher(proxy=config.proxy)
        self.papers = PaperSearcher(proxy=config.proxy)
        self.github = GitHubAnalyzer()
        self.indexer = ChromaIndexer(persist_dir=config.knowledge.resolved_chroma_path)
        self.graph = KnowledgeGraph.load(config.knowledge.resolved_graph_path)

    def search(self, topic: str) -> dict:
        """Run all searchers for a topic. Returns categorized results."""
        results = {
            "web": self.web.search(topic, num_results=5),
            "papers": self.papers.search(topic, max_results=5),
            "github": self.github.search(topic, max_results=5),
        }
        # Index results
        for source_type, items in results.items():
            docs = []
            for item in items:
                text = item.content or item.snippet
                docs.append({
                    "id": f"{source_type}_{hash(item.url) % 100000:05d}",
                    "text": text,
                    "metadata": {"source": source_type, "url": item.url, "title": item.title},
                })
            if docs:
                self.indexer.add_documents(docs, collection="knowledge")
        # Index into knowledge graph
        for items in results.values():
            for item in items:
                self.graph.auto_index([item])
        # Persist graph
        self.graph.save(self.config.knowledge.resolved_graph_path)
        return results

    def summarize(self, results: dict) -> str:
        """Generate a text summary of research results for LLM context."""
        lines = ["## Research Summary\n"]
        for source_type, items in results.items():
            lines.append(f"### {source_type.upper()}\n")
            for item in items:
                title = getattr(item, "title", getattr(item, "repo", "?"))
                snippet = getattr(item, "snippet", getattr(item, "description", ""))[:200]
                lines.append(f"- **{title}**: {snippet}")
            if not items:
                lines.append("_(no results)_")
            lines.append("")
        return "\n".join(lines)

    def search_knowledge(self, query: str, top_k: int = 5) -> list[dict]:
        """Semantic search through indexed knowledge."""
        return self.indexer.search(query, top_k=top_k)

    def open_wiki(self, serve: bool = False):
        """Open LLM Wiki."""
        if serve:
            server = WikiServer(self.graph, self.indexer)
            server.run()
        else:
            cli = WikiCLI(self.graph, self.indexer)
            cli.run()
```

- [ ] **Step 2: Verify import works**

Run: `.venv/bin/python -c "from ppt_agent.research.manager import ResearchManager; print('OK')"`
Expected: "OK"

- [ ] **Step 3: Commit**

```
git add src/ppt_agent/research/manager.py
git commit -m "feat: add ResearchManager orchestrating all research components"
```

---

### Task 10: Integrate research into orchestrator + CLI

**Files:**
- Modify: `src/ppt_agent/orchestrator.py`
- Modify: `src/ppt_agent/cli.py`

- [ ] **Step 1: Update orchestrator to add research phase**

In `run_new_project`, add after `console.print(Panel(...))`:

```python
    # Research phase
    console.print(Panel("[bold]正在搜索相关知识...[/bold]", style="blue"))
    from ppt_agent.research.manager import ResearchManager
    research_mgr = ResearchManager(config)
    results = research_mgr.search(topic)
    summary = research_mgr.summarize(results)
    session.add_message("system", f"Research results:\n{summary}")
    console.print(f"[green]✓ 找到 {len(results['web'])} 篇网页、{len(results['papers'])} 篇论文、{len(results['github'])} 个相关项目[/green]")
```

And update the SYSTEM_PROMPT to include the research summary context:

```python
SYSTEM_PROMPT = """你是PPT Agent，一个专业的技术解决方案PPT生成助手。

你的工作流程：
1. 与用户讨论PPT思路，了解背景、受众、核心论点
2. 基于讨论结果，提出清晰的slide框架（标题+每页类型+核心内容）
3. 确认框架后，生成精美的.pptx文件

风格要求：
- 逻辑清晰，抽象层次合理
- 内容精炼，避免堆砌
- 适合企业技术方案汇报场景

当前阶段：讨论阶段。请与用户深入交流，不要急于定框架。

以下是关于该主题的研究资料摘要，供参考：\n\n{research_summary}"""
```

And in the discussion loop, substitute `{research_summary}`:

```python
    system_prompt = SYSTEM_PROMPT.replace("{research_summary}", summary)
    messages = [
        {"role": "system", "content": system_prompt},
        *[{"role": m["role"], "content": m["content"]} for m in session.messages[-10:]],
    ]
```

- [ ] **Step 2: Add `wiki` CLI command**

Add to `cli.py`:

```python
@cli.command()
@click.option("--serve", is_flag=True, help="Start web server instead of CLI")
@click.pass_context
def wiki(ctx, serve):
    """Open LLM Wiki browser."""
    from ppt_agent.research.manager import ResearchManager
    mgr = ResearchManager(ctx.obj["config"])
    mgr.open_wiki(serve=serve)
```

- [ ] **Step 3: Run full test suite**

Run: `.venv/bin/python -m pytest tests/ -v`
Expected: all pass (including any new research tests)

- [ ] **Step 4: Verify CLI works**

Run: `.venv/bin/python -m ppt_agent --help`
Expected: shows `wiki` command

- [ ] **Step 5: Commit**

```
git add src/ppt_agent/orchestrator.py src/ppt_agent/cli.py
git commit -m "feat: integrate research pipeline into orchestrator and CLI"
```

---

### Self-review / Spec coverage

After all tasks, verify:
```bash
.venv/bin/python -m pytest tests/ -v
# Expected: all tests pass

.venv/bin/python -m ppt_agent --help
# Expected: shows wiki command

.venv/bin/python -c "from ppt_agent.research.manager import ResearchManager; print('Research pipeline ready')"
# Expected: Research pipeline ready
```

**Spec coverage checklist:**
- [x] Web search (agent-reach + fallback + proxy) — Task 3
- [x] Paper search (arXiv + Semantic Scholar) — Task 4
- [x] GitHub analysis — Task 5
- [x] Content extraction (HTML→Markdown, README summary) — Task 2
- [x] ChromaDB vector storage — Task 7
- [x] Knowledge graph (NetworkX) — Task 6
- [x] LLM Wiki CLI — Task 8
- [x] LLM Wiki HTML (Flask) — Task 8
- [x] ResearchManager wiring — Task 9
- [x] Orchestrator integration — Task 10
- [x] Wiki CLI command — Task 10
- [x] Proxy configuration — Task 1
- [x] Timeliness metadata — Task 1 (SearchResult.collected_at)
- [x] Configuration (KnowledgeConfig) — Task 1
