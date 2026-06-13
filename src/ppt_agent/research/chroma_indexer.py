from __future__ import annotations
from pathlib import Path
import chromadb
from chromadb.config import Settings


class ChromaIndexer:
    def __init__(self, persist_dir: str = ""):
        if not persist_dir:
            persist_dir = str(Path.home() / ".ppt-agent" / "knowledge" / "chroma")
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
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
        col.add(documents=[text], metadatas=[metadata or {}], ids=[id])

    def add_documents(self, documents: list[dict], collection: str = "knowledge"):
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
