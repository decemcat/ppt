from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field
from ppt_agent.models import PPTFramework


class Critique(BaseModel):
    point: str
    severity: Literal["critical", "important", "minor"]
    suggestion: str


class ContestedPoint(BaseModel):
    critique: Critique
    defense: str
    judge_verdict: Literal["accept", "reject", "undecided"]
    reason: str


class DebateRound(BaseModel):
    round_number: int
    critiques: list[Critique] = Field(default_factory=list)
    defenses: list[str] = Field(default_factory=list)
    contested: list[ContestedPoint] = Field(default_factory=list)
    judge_notes: str = ""


class DebateResult(BaseModel):
    original_framework: PPTFramework
    rounds: list[DebateRound] = Field(default_factory=list)
    final_framework: PPTFramework
    improvements: list[str] = Field(default_factory=list)
    logic_score: float = 0.0
    human_rulings: list[str] = Field(default_factory=list)
