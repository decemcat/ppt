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


class TestKnowledgeModels:
    def test_node_creation(self):
        n = KnowledgeNode(id="k8s", label="Kubernetes", type="concept", summary="Container orchestration", sources=[])
        assert n.type == "concept"

    def test_edge_creation(self):
        e = KnowledgeEdge(source_id="k8s", target_id="docker", relation="extends")
        assert e.relation == "extends"
