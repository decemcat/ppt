# Style Learning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extract style patterns from example .pptx files, persist as StyleProfile, apply during PPT generation.

**Architecture:** StyleExtractor analyzes a .pptx template → produces StyleProfile (colors, fonts, layout patterns, spacing ratios) → saved as YAML. ShapeRenderer reads StyleProfile to apply colors/fonts/spacing during rendering.

---

## File Structure

```
src/ppt_agent/
├── style/
│   ├── __init__.py
│   ├── extractor.py       # Extract style from .pptx
│   └── profile.py         # StyleProfile model + persistence
├── generator/
│   └── shape_renderer.py  # MODIFY — apply StyleProfile
├── config.py              # MODIFY — add style_path field
└── cli.py                 # MODIFY — add style commands
tests/
└── test_style.py
```

---

### Task 1: StyleProfile model + extractor + persistence

- [ ] **Step 1:** Create `src/ppt_agent/style/__init__.py` (empty)

- [ ] **Step 2:** Create `src/ppt_agent/style/profile.py`:

```python
from __future__ import annotations
from pathlib import Path
import yaml
from pydantic import BaseModel, Field


class ColorScheme(BaseModel):
    primary: str = "#1F4E79"
    secondary: str = "#2E75B6"
    accent: str = "#D6E4F0"
    background: str = "#FFFFFF"
    text_primary: str = "#1F4E79"
    text_secondary: str = "#333333"
    text_light: str = "#FFFFFF"


class FontProfile(BaseModel):
    title_font: str = "微软雅黑"
    title_size: int = 32
    subtitle_font: str = "微软雅黑"
    subtitle_size: int = 20
    body_font: str = "微软雅黑"
    body_size: int = 14
    caption_font: str = "微软雅黑"
    caption_size: int = 11


class LayoutRatios(BaseModel):
    title_height_ratio: float = 0.15
    content_margin_ratio: float = 0.08
    column_gap_ratio: float = 0.05
    element_spacing_ratio: float = 0.03


class StyleProfile(BaseModel):
    name: str = "default"
    colors: ColorScheme = Field(default_factory=ColorScheme)
    fonts: FontProfile = Field(default_factory=FontProfile)
    layout: LayoutRatios = Field(default_factory=LayoutRatios)
    source_file: str = ""

    def save(self, dir_path: str | None = None) -> str:
        save_dir = Path(dir_path or Path.home() / ".ppt-agent" / "styles")
        save_dir.mkdir(parents=True, exist_ok=True)
        path = save_dir / f"{self.name}.yaml"
        path.write_text(yaml.dump(self.model_dump(), allow_unicode=True, default_flow_style=False), encoding="utf-8")
        return str(path)

    @classmethod
    def load(cls, name: str, dir_path: str | None = None) -> "StyleProfile":
        load_dir = Path(dir_path or Path.home() / ".ppt-agent" / "styles")
        path = load_dir / f"{name}.yaml"
        if not path.exists():
            raise FileNotFoundError(f"Style profile '{name}' not found at {path}")
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return cls(**data)

    @classmethod
    def list_profiles(cls, dir_path: str | None = None) -> list[str]:
        load_dir = Path(dir_path or Path.home() / ".ppt-agent" / "styles")
        if not load_dir.exists():
            return []
        return sorted(p.stem for p in load_dir.glob("*.yaml"))
```

- [ ] **Step 3:** Create `src/ppt_agent/style/extractor.py`:

```python
from __future__ import annotations
from collections import Counter
from pptx import Presentation
from pptx.util import Emu, Pt
from pptx.enum.text import PP_ALIGN
from ppt_agent.style.profile import StyleProfile, ColorScheme, FontProfile, LayoutRatios


def _rgb_to_hex(rgb) -> str:
    if rgb is None:
        return "#333333"
    return f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"


def _most_common(items: list) -> str:
    if not items:
        return "#333333"
    counter = Counter(items)
    return counter.most_common(1)[0][0]


class StyleExtractor:
    @staticmethod
    def extract(pptx_path: str, name: str = "extracted") -> StyleProfile:
        prs = Presentation(pptx_path)
        colors = StyleExtractor._extract_colors(prs)
        fonts = StyleExtractor._extract_fonts(prs)
        layout = StyleExtractor._extract_layout(prs)
        return StyleProfile(
            name=name,
            colors=colors,
            fonts=fonts,
            layout=layout,
            source_file=pptx_path,
        )

    @staticmethod
    def _extract_colors(prs: Presentation) -> ColorScheme:
        bg_colors = []
        text_colors = []
        fill_colors = []
        for slide in prs.slides:
            if slide.background.fill.fore_color.rgb:
                bg_colors.append(_rgb_to_hex(slide.background.fill.fore_color.rgb))
            for shape in slide.shapes:
                if shape.has_text_frame:
                    for para in shape.text_frame.paragraphs:
                        for run in para.runs:
                            if run.font.color and run.font.color.rgb:
                                text_colors.append(_rgb_to_hex(run.font.color.rgb))
                if hasattr(shape, "fill") and shape.fill.fore_color and shape.fill.fore_color.rgb:
                    fill_colors.append(_rgb_to_hex(shape.fill.fore_color.rgb))
        background = _most_common(bg_colors) if bg_colors else "#FFFFFF"
        primary = _most_common(fill_colors) if fill_colors else "#1F4E79"
        text_primary = _most_common(text_colors) if text_colors else "#333333"
        secondary = fill_colors[1] if len(fill_colors) > 1 else primary
        return ColorScheme(
            primary=primary,
            secondary=secondary,
            accent=_rgb_to_hex(prs.slide_masters[0].background.fill.fore_color.rgb) if prs.slide_masters[0].background.fill.fore_color.rgb else "#D6E4F0",
            background=background,
            text_primary=text_primary,
            text_secondary="#333333",
            text_light="#FFFFFF",
        )

    @staticmethod
    def _extract_fonts(prs: Presentation) -> FontProfile:
        title_fonts = []
        title_sizes = []
        body_fonts = []
        body_sizes = []
        for slide in prs.slides:
            for shape in slide.shapes:
                if not shape.has_text_frame:
                    continue
                for para in shape.text_frame.paragraphs:
                    for run in para.runs:
                        font_name = run.font.name
                        font_size = run.font.size
                        if font_name:
                            if para.alignment in (PP_ALIGN.CENTER, None) and font_size and font_size >= Pt(24):
                                title_fonts.append(font_name)
                                title_sizes.append(int(font_size / Pt(1)))
                            else:
                                body_fonts.append(font_name)
                                if font_size:
                                    body_sizes.append(int(font_size / Pt(1)))
        title_font = _most_common(title_fonts) if title_fonts else "微软雅黑"
        body_font = _most_common(body_fonts) if body_fonts else "微软雅黑"
        return FontProfile(
            title_font=title_font,
            title_size=_most_common(title_sizes) if title_sizes else 32,
            subtitle_font=title_font,
            subtitle_size=max(int((_most_common(title_sizes) if title_sizes else 32) * 0.65), 14),
            body_font=body_font,
            body_size=_most_common(body_sizes) if body_sizes else 14,
            caption_font=body_font,
            caption_size=max(int((_most_common(body_sizes) if body_sizes else 14) * 0.8), 10),
        )

    @staticmethod
    def _extract_layout(prs: Presentation) -> LayoutRatios:
        slide_height = prs.slide_height
        title_heights = []
        for slide in prs.slides:
            for shape in slide.shapes:
                if shape.has_text_frame and shape.top < Emu(slide_height // 3):
                    max_font = 0
                    for para in shape.text_frame.paragraphs:
                        for run in para.runs:
                            if run.font.size and run.font.size > max_font:
                                max_font = run.font.size
                    if max_font >= Pt(24):
                        title_heights.append(shape.top + shape.height)
        if title_heights:
            avg_title_h = sum(title_heights) / len(title_heights)
            title_ratio = round(float(avg_title_h / slide_height), 2)
        else:
            title_ratio = 0.15
        return LayoutRatios(
            title_height_ratio=title_ratio,
            content_margin_ratio=0.08,
            column_gap_ratio=0.05,
            element_spacing_ratio=0.03,
        )
```

- [ ] **Step 4:** Create `tests/test_style.py`:

```python
import tempfile
from pathlib import Path
from ppt_agent.style.profile import StyleProfile, ColorScheme, FontProfile, LayoutRatios
from ppt_agent.style.extractor import StyleExtractor


class TestStyleProfile:
    def test_default_profile(self):
        p = StyleProfile(name="test")
        assert p.colors.primary == "#1F4E79"
        assert p.fonts.title_font == "微软雅黑"

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            profile = StyleProfile(name="my_style", colors=ColorScheme(primary="#FF0000"))
            path = profile.save(tmp)
            loaded = StyleProfile.load("my_style", tmp)
            assert loaded.colors.primary == "#FF0000"

    def test_list_profiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            StyleProfile(name="a").save(tmp)
            StyleProfile(name="b").save(tmp)
            names = StyleProfile.list_profiles(tmp)
            assert "a" in names
            assert "b" in names

    def test_load_missing_raises(self):
        try:
            StyleProfile.load("nonexistent", "/tmp/empty_dir_test")
            assert False, "Should have raised"
        except FileNotFoundError:
            pass


class TestStyleExtractor:
    def test_extractor_class_exists(self):
        assert hasattr(StyleExtractor, "extract")
```

- [ ] **Step 5:** Run tests: `.venv/bin/python -m pytest tests/test_style.py -v`

- [ ] **Step 6:** Integrate with shape_renderer.py. Read the existing `src/ppt_agent/generator/shape_renderer.py` first. Add a `style_profile` optional parameter to `ShapeRenderer.__init__` and use it to override colors/fonts when rendering. Add at minimum:

```python
# In __init__:
    self.style_profile = style_profile  # Optional[StyleProfile]

# When setting title color:
    if self.style_profile:
        run.font.color.rgb = RGBColor.from_string(self.style_profile.colors.text_primary.lstrip("#"))
        run.font.name = self.style_profile.fonts.title_font
        run.font.size = Pt(self.style_profile.fonts.title_size)
```

Apply the same pattern for body text, subtitle, fills, etc. Read the file to understand the current rendering logic first.

- [ ] **Step 7:** Wire StyleProfile into orchestrator. In `src/ppt_agent/orchestrator.py`, before calling the slide generator, load the style profile if one is specified in config or available:

```python
    style_profile = None
    if config.style_path and Path(config.style_path).exists():
        from ppt_agent.style.profile import StyleProfile
        style_profile = StyleProfile.load(Path(config.style_path).stem)
```

Pass `style_profile` to the generator/rendering pipeline.

- [ ] **Step 8:** Add config field. In `src/ppt_agent/config.py`, add to Config class:

```python
    style_path: str | None = None
```

- [ ] **Step 9:** Add CLI commands. In `src/ppt_agent/cli.py`, add a new click group or commands:

```python
@cli.command("style-extract")
@click.argument("pptx_path")
@click.option("--name", default="extracted", help="Style profile name")
def style_extract(pptx_path: str, name: str):
    """Extract style profile from a .pptx file."""
    from ppt_agent.style.extractor import StyleExtractor
    profile = StyleExtractor.extract(pptx_path, name)
    path = profile.save()
    click.echo(f"Style profile '{name}' saved to {path}")

@cli.command("style-list")
def style_list():
    """List saved style profiles."""
    from ppt_agent.style.profile import StyleProfile
    profiles = StyleProfile.list_profiles()
    if profiles:
        for p in profiles:
            click.echo(p)
    else:
        click.echo("No style profiles found.")

@cli.command("style-show")
@click.argument("name")
def style_show(name: str):
    """Show details of a style profile."""
    from ppt_agent.style.profile import StyleProfile
    profile = StyleProfile.load(name)
    click.echo(yaml.dump(profile.model_dump(), allow_unicode=True, default_flow_style=False))
```

Also add `--style` option to the `new` command:
```python
@click.option("--style", "style_name", help="Apply saved style profile")
```
And in the function body:
```python
    if style_name:
        config.style_path = str(Path.home() / ".ppt-agent" / "styles" / f"{style_name}.yaml")
```

- [ ] **Step 10:** Run full test suite: `.venv/bin/python -m pytest tests/ -v`

- [ ] **Step 11:** Verify CLI: `.venv/bin/python -m ppt_agent --help` shows new style commands

- [ ] **Step 12:** Commit

```
git add src/ppt_agent/style/ tests/test_style.py src/ppt_agent/generator/shape_renderer.py src/ppt_agent/orchestrator.py src/ppt_agent/config.py src/ppt_agent/cli.py docs/superpowers/
git commit -m "feat: add style learning with extractor, profile persistence, and CLI"
```
