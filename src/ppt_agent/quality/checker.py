from __future__ import annotations
from rich.console import Console
from ppt_agent.config import Config
from ppt_agent.llm.router import ModelRouter
from ppt_agent.quality.slide_capture import SlideCapture
from ppt_agent.quality.vision_judge import VisionJudge
from pydantic import BaseModel, Field


console = Console()


class SlideScore(BaseModel):
    slide_index: int
    layout_balance: float = 0.0
    text_density: float = 0.0
    color_consistency: float = 0.0
    visual_hierarchy: float = 0.0
    cleanliness: float = 0.0
    overall: float = 0.0
    issues: list[str] = Field(default_factory=list)


class VisualCheckResult(BaseModel):
    scores: list[SlideScore] = Field(default_factory=list)
    total_score: float = 0.0
    passed: bool = True
    summary: str = ""


class VisualQualityChecker:
    def __init__(self, config: Config, router: ModelRouter):
        self.config = config
        vc = config.visual_check
        if vc.provider != "auto" and vc.model:
            provider = router.get_provider(vc.provider)
            model = vc.model
        else:
            provider, model = router.get_model("visual_check")
        self.judge = VisionJudge(provider, model)
        self.threshold = vc.threshold

    def check(self, pptx_path: str) -> VisualCheckResult:
        images = SlideCapture.pptx_to_images(pptx_path)
        if not images:
            return VisualCheckResult(
                passed=True,
                summary="LibreOffice unavailable, visual check skipped. Shape-level quality check was done during generation.",
            )
        scores = []
        for i, img_path in enumerate(images):
            with console.status(f"评审第 {i+1}/{len(images)} 页..."):
                result = self.judge.evaluate_slide(img_path)
                scores.append(SlideScore(
                    slide_index=i,
                    layout_balance=result.get("layout_balance", 0),
                    text_density=result.get("text_density", 0),
                    color_consistency=result.get("color_consistency", 0),
                    visual_hierarchy=result.get("visual_hierarchy", 0),
                    cleanliness=result.get("cleanliness", 0),
                    overall=result.get("overall", 0),
                    issues=result.get("issues", []),
                ))
        total = sum(s.overall for s in scores) / len(scores) if scores else 0
        return VisualCheckResult(
            scores=scores,
            total_score=round(total, 1),
            passed=total >= self.threshold,
            summary=self._build_summary(scores, total),
        )

    def _build_summary(self, scores: list[SlideScore], total: float) -> str:
        lines = [f"视觉质检总评: {total:.1f}/10"]
        for s in scores:
            status = "✓" if s.overall >= self.threshold else "⚠"
            lines.append(f"  {status} 第{s.slide_index+1}页: {s.overall:.1f}/10")
            if s.issues:
                for issue in s.issues:
                    lines.append(f"    - {issue}")
        return "\n".join(lines)
