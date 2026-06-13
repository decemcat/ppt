# Visual Quality Check Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add vision-model-based visual quality checking that evaluates PPT slide layout, text density, color consistency, visual hierarchy, and cleanliness per slide.

**Architecture:** SlideCapture converts .pptx to PNG images via LibreOffice headless (optional). VisionJudge sends images to a vision LLM for per-slide scoring. VisualQualityChecker orchestrates both and produces VisualCheckResult.

**Tech Stack:** Python 3.11+, pydantic, existing LLM provider layer, LibreOffice (optional).

---

## File Structure

```
src/ppt_agent/
├── config.py              # MODIFY — add VisualCheckConfig
├── orchestrator.py        # MODIFY — add visual check after generation
├── cli.py                 # MODIFY — add --no-visual-check flag
└── quality/
    ├── __init__.py
    ├── slide_capture.py   # .pptx → PNG via LibreOffice
    ├── vision_judge.py    # Vision LLM evaluation
    └── checker.py         # VisualQualityChecker orchestrator
tests/
├── test_visual_check.py
```

---

### Task 1: Models + config + slide capture + vision judge + checker + integration

**Files:**
- Create: `src/ppt_agent/quality/__init__.py`
- Create: `src/ppt_agent/quality/slide_capture.py`
- Create: `src/ppt_agent/quality/vision_judge.py`
- Create: `src/ppt_agent/quality/checker.py`
- Create: `tests/test_visual_check.py`
- Modify: `src/ppt_agent/config.py`
- Modify: `src/ppt_agent/orchestrator.py`
- Modify: `src/ppt_agent/cli.py`

- [ ] **Step 1: Create quality package init**

```python
# src/ppt_agent/quality/__init__.py
```

- [ ] **Step 2: Write slide capture**

```python
# src/ppt_agent/quality/slide_capture.py
from __future__ import annotations
import subprocess
import shutil
from pathlib import Path
from pptx import Presentation


class SlideCapture:
    @staticmethod
    def pptx_to_images(pptx_path: str, output_dir: str | None = None) -> list[str]:
        """Convert .pptx to PNG images using LibreOffice headless.

        Returns list of image paths. Returns empty list if LibreOffice unavailable.
        """
        soffice = shutil.which("soffice") or shutil.which("libreoffice")
        if not soffice:
            return []
        if output_dir is None:
            import tempfile
            output_dir = tempfile.mkdtemp()
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        try:
            result = subprocess.run(
                [soffice, "--headless", "--convert-to", "png", "--outdir", output_dir, pptx_path],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode != 0:
                return []
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return []
        return sorted(str(p) for p in Path(output_dir).glob("*.png"))

    @staticmethod
    def is_available() -> bool:
        return (shutil.which("soffice") or shutil.which("libreoffice")) is not None
```

- [ ] **Step 3: Write vision judge**

```python
# src/ppt_agent/quality/vision_judge.py
from __future__ import annotations
import json
import base64
from pathlib import Path
from ppt_agent.llm.base import LLMProvider
from ppt_agent.llm.router import ModelRouter


VISION_PROMPT = """你是PPT排版评审专家。请对以下幻灯片截图进行评审。

评分维度（0-10分）：
1. 布局平衡（layout_balance）：元素是否均衡分布？有无偏重或留白不当？
2. 文字密度（text_density）：文字量是否适中？是否过于拥挤或过于稀疏？
3. 配色一致性（color_consistency）：配色是否统一和谐？有无突兀颜色？
4. 视觉层级（visual_hierarchy）：标题/正文/图表的层级是否清晰？
5. 整洁度（cleanliness）：整体是否简洁专业？有无花哨装饰？

严格按以下JSON格式输出，不要输出其他内容：
{"layout_balance":0,"text_density":0,"color_consistency":0,"visual_hierarchy":0,"cleanliness":0,"overall":0,"issues":[]}"""


class VisionJudge:
    def __init__(self, provider: LLMProvider, model: str):
        self.provider = provider
        self.model = model

    def evaluate_slide(self, image_path: str) -> dict:
        """Evaluate a single slide image. Returns score dict."""
        try:
            return self._evaluate_with_api(image_path)
        except Exception:
            return {
                "layout_balance": 0, "text_density": 0, "color_consistency": 0,
                "visual_hierarchy": 0, "cleanliness": 0, "overall": 0, "issues": ["视觉评审失败"],
            }

    def _evaluate_with_api(self, image_path: str) -> dict:
        img_data = base64.b64encode(Path(image_path).read_bytes()).decode()
        ext = Path(image_path).suffix.lstrip(".")
        import openai
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model=self.model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": VISION_PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:image/{ext};base64,{img_data}"}},
                ],
            }],
            max_tokens=500,
        )
        text = response.choices[0].message.content or ""
        # Strip markdown code fences if present
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        return json.loads(text)
```

- [ ] **Step 4: Write quality checker**

```python
# src/ppt_agent/quality/checker.py
from __future__ import annotations
from rich.console import Console
from ppt_agent.config import Config
from ppt_agent.llm.router import ModelRouter
from ppt_agent.quality.slide_capture import SlideCapture
from ppt_agent.quality.vision_judge import VisionJudge
from pydantic import BaseModel, Field
from typing import Literal


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
        provider, model = router.get_model("daily_chat")
        self.judge = VisionJudge(provider, model)
        self.threshold = config.visual_check.threshold

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
```

- [ ] **Step 5: Add VisualCheckConfig to config.py**

```python
class VisualCheckConfig(BaseModel):
    enabled: bool = True
    threshold: float = 7.0
    provider: str = "auto"
```

Add to Config class:
```python
    visual_check: VisualCheckConfig = Field(default_factory=VisualCheckConfig)
```

- [ ] **Step 6: Write tests**

```python
# tests/test_visual_check.py
from ppt_agent.quality.checker import SlideScore, VisualCheckResult


class TestVisualCheck:
    def test_slide_score_defaults(self):
        s = SlideScore(slide_index=0)
        assert s.overall == 0.0
        assert len(s.issues) == 0

    def test_visual_check_result(self):
        r = VisualCheckResult(passed=True, summary="ok", total_score=8.0)
        assert r.passed is True

    def test_check_result_with_scores(self):
        scores = [
            SlideScore(slide_index=0, overall=8.0),
            SlideScore(slide_index=1, overall=6.0, issues=["文字过密"]),
        ]
        r = VisualCheckResult(scores=scores, total_score=7.0, passed=True)
        assert len(r.scores) == 2

    def test_slide_capture_not_available(self):
        from ppt_agent.quality.slide_capture import SlideCapture
        # Just verify the class exists and is_available returns bool
        assert isinstance(SlideCapture.is_available(), bool)
```

- [ ] **Step 7: Integrate into orchestrator**

In `orchestrator.py`, after `generate_pptx()` call in `run_new_project`, add:

```python
    # Visual quality check
    if config.visual_check.enabled:
        from ppt_agent.quality.checker import VisualQualityChecker
        checker = VisualQualityChecker(config, router)
        check_result = checker.check(output)
        console.print(check_result.summary)
        if not check_result.passed:
            console.print(f"[yellow]⚠️ 视觉质检评分 {check_result.total_score:.1f}/10，低于阈值 {config.visual_check.threshold}[/yellow]")
```

- [ ] **Step 8: Add CLI flag**

In `cli.py`, add to `new` command options:
```python
@click.option("--no-visual-check", is_flag=True, help="Skip visual quality check")
```

And in the function body:
```python
    if no_visual_check:
        config.visual_check.enabled = False
```

- [ ] **Step 9: Run full test suite**

Run: `.venv/bin/python -m pytest tests/ -v`

- [ ] **Step 10: Verify CLI**

Run: `.venv/bin/python -m ppt_agent new --help`
Expected: shows `--no-visual-check`

- [ ] **Step 11: Commit**

```
git add src/ppt_agent/quality/ tests/test_visual_check.py src/ppt_agent/config.py src/ppt_agent/orchestrator.py src/ppt_agent/cli.py
git commit -m "feat: add visual quality check with vision model evaluation"
```
