from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field


class ArchNode(BaseModel):
    id: str
    label: str
    children: list[str] = Field(default_factory=list)
    style: Literal["group", "component", "datastore"] = "component"


class ArchEdge(BaseModel):
    from_id: str = Field(alias="from_id")
    to_id: str
    label: str = ""
    style: Literal["solid", "dashed", "arrow"] = "arrow"


class ArchDiagram(BaseModel):
    type: Literal["layered", "flow", "radial", "grid"]
    nodes: list[ArchNode]
    edges: list[ArchEdge] = Field(default_factory=list)


class SlideContent(BaseModel):
    title: str
    slide_type: Literal["title", "text", "arch_diagram", "bullets", "section_header"]
    diagram: ArchDiagram | None = None
    bullets: list[str] = Field(default_factory=list)
    notes: str = ""


class SlideFramework(BaseModel):
    slides: list[SlideContent]


class PPTFramework(BaseModel):
    title: str
    framework: SlideFramework
