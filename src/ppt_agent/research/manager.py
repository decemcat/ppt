from __future__ import annotations
from ppt_agent.config import Config
from ppt_agent.research.web_searcher import WebSearcher
from ppt_agent.research.paper_searcher import PaperSearcher
from ppt_agent.research.github_analyzer import GitHubAnalyzer
from ppt_agent.research.chroma_indexer import ChromaIndexer
from ppt_agent.research.knowledge_graph import KnowledgeGraph
from ppt_agent.research.wiki import WikiCLI, WikiServer


class ResearchManager:
    def __init__(self, config: Config):
        self.config = config
        self.web = WebSearcher(proxy=config.proxy)
        self.papers = PaperSearcher(proxy=config.proxy)
        self.github = GitHubAnalyzer()
        self.indexer = ChromaIndexer(persist_dir=config.knowledge.resolved_chroma_path)
        self.graph = KnowledgeGraph.load(config.knowledge.resolved_graph_path)

    def search(self, topic: str) -> dict:
        results = {
            "web": self.web.search(topic, num_results=5),
            "papers": self.papers.search(topic, max_results=5),
            "github": self.github.search(topic, max_results=5),
        }
        for source_type, items in results.items():
            docs = []
            for item in items:
                text = getattr(item, "content", "") or getattr(item, "snippet", "") or getattr(item, "description", "")
                url = getattr(item, "url", "")
                title = getattr(item, "title", "") or getattr(item, "repo", "")
                docs.append({
                    "id": f"{source_type}_{hash(url) % 100000:05d}",
                    "text": text,
                    "metadata": {"source": source_type, "url": url, "title": title},
                })
            if docs:
                self.indexer.add_documents(docs, collection="knowledge")
        for items in results.values():
            search_results = [item for item in items if hasattr(item, "source")]
            self.graph.auto_index(search_results)
        self.graph.save(self.config.knowledge.resolved_graph_path)
        return results

    def summarize(self, results: dict) -> str:
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
        return self.indexer.search(query, top_k=top_k)

    def open_wiki(self, serve: bool = False):
        if serve:
            server = WikiServer(self.graph, self.indexer)
            server.run()
        else:
            cli = WikiCLI(self.graph, self.indexer)
            cli.run()
