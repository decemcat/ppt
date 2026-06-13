from __future__ import annotations
from datetime import datetime, date
from typing import Literal
from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    url: str
    title: str
    snippet: str
    content: str = ""
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
