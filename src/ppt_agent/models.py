from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class ArchNode(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    label: str
    children: list[str] = Field(default_factory=list)
    style: Literal["group", "component", "datastore"] = "component"


class ArchEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")
    from_id: str
    to_id: str
    label: str = ""
    style: Literal["solid", "dashed", "arrow"] = "arrow"


class ArchDiagram(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["layered", "flow", "radial", "grid"]
    nodes: list[ArchNode]
    edges: list[ArchEdge] = Field(default_factory=list)


class SlideContent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str
    slide_type: Literal["title", "text", "arch_diagram", "bullets", "section_header"]
    diagram: ArchDiagram | None = None
    bullets: list[str] = Field(default_factory=list)
    notes: str = ""


class SlideFramework(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slides: list[SlideContent]


class PPTFramework(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str
    framework: SlideFramework
