from __future__ import annotations
from pathlib import Path
import json
import networkx as nx
from networkx.readwrite import json_graph
from ppt_agent.research.models import KnowledgeNode, KnowledgeEdge, SearchResult


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
            id=node_id, label=data.get("label", node_id),
            type=data.get("type", "concept"), summary=data.get("summary", ""),
            sources=data.get("sources", []),
        )

    def find_path(self, source_id: str, target_id: str) -> list[str]:
        try:
            return nx.shortest_path(self._graph, source_id, target_id)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []

    def get_related(self, node_id: str, max_depth: int = 2) -> list[KnowledgeNode]:
        if not self._graph.has_node(node_id):
            return []
        related = set()
        for node in nx.dfs_preorder_nodes(self._graph, source=node_id, depth_limit=max_depth):
            related.add(node)
        for node in nx.dfs_preorder_nodes(self._graph.reverse(), source=node_id, depth_limit=max_depth):
            related.add(node)
        return [self.get_node(n) for n in related if n != node_id and self.get_node(n) is not None]

    def search_nodes(self, query: str) -> list[KnowledgeNode]:
        query_lower = query.lower()
        results = []
        for node_id in self._graph.nodes:
            data = self._graph.nodes[node_id]
            if query_lower in data.get("label", "").lower() or query_lower in data.get("summary", "").lower():
                results.append(self.get_node(node_id))
        return results

    def save(self, path: str):
        data = json_graph.node_link_data(self._graph)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: str) -> KnowledgeGraph:
        kg = cls()
        if Path(path).exists():
            with open(path) as f:
                data = json.load(f)
            kg._graph = json_graph.node_link_graph(data, directed=True)
        return kg

    def count(self) -> dict:
        return {"nodes": self._graph.number_of_nodes(), "edges": self._graph.number_of_edges()}

    def auto_index(self, results: list[SearchResult]):
        for r in results:
            node_id = r.url.split("/")[-1][:50] or r.title[:50]
            source_type = {"web": "concept", "paper": "paper", "github": "project"}.get(r.source, "concept")
            node = KnowledgeNode(
                id=node_id, label=r.title[:100], type=source_type,
                summary=r.snippet[:500], sources=[r.url],
            )
            self.add_node(node)
