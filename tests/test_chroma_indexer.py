from ppt_agent.research.chroma_indexer import ChromaIndexer


class TestChromaIndexer:
    def test_init(self, tmp_path):
        indexer = ChromaIndexer(persist_dir=str(tmp_path / "chroma"))
        assert indexer is not None

    def test_add_and_search(self, tmp_path):
        indexer = ChromaIndexer(persist_dir=str(tmp_path / "chroma"))
        indexer.add_document(id="doc1", text="Kubernetes for AI training", metadata={"source": "web"})
        results = indexer.search("AI training", top_k=5)
        assert len(results) > 0

    def test_search_by_source(self, tmp_path):
        indexer = ChromaIndexer(persist_dir=str(tmp_path / "chroma"))
        indexer.add_document(id="w1", text="Web article about ML", metadata={"source": "web"})
        indexer.add_document(id="p1", text="Paper about deep learning", metadata={"source": "paper"})
        results = indexer.search("ML", top_k=5, source_filter="web")
        assert all(r["metadata"].get("source") == "web" for r in results)
