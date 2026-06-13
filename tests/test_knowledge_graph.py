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
