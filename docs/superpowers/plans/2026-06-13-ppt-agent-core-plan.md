# PPT Agent Core Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the CLI framework, conversation orchestrator, template analyzer, and PPT generator (Shape Renderer + Image Fallback) for the PPT Agent.

**Architecture:** Click-based CLI orchestrates a state-machine conversation flow. User input → LLM discussion → framework confirmation → structured data → Shape Renderer (python-pptx). Shape output is self-checked; low scores trigger Image Fallback (Mermaid→SVG→PNG). Template analyzer extracts theme from a `.pptx` file and passes it to all rendering.

**Tech Stack:** Python 3.11+, click, rich, pydantic, python-pptx, pyyaml, pytest, openai/anthropic SDK.

---

## File Structure

```
/Users/decemwind/workspace/ppt/
├── pyproject.toml
├── src/ppt_agent/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── config.py
│   ├── models.py
│   ├── session.py
│   ├── orchestrator.py
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── openai_provider.py
│   │   ├── anthropic_provider.py
│   │   └── router.py
│   ├── template/
│   │   ├── __init__.py
│   │   └── analyzer.py
│   └── generator/
│       ├── __init__.py
│       ├── slide_generator.py
│       ├── shape_renderer.py
│       ├── image_fallback.py
│       └── quality_check.py
└── tests/
    ├── __init__.py
    ├── test_models.py
    ├── test_config.py
    ├── test_session.py
    ├── test_template_analyzer.py
    ├── test_shape_renderer.py
    ├── test_quality_check.py
    └── fixtures/
        └── minimal_template.pptx
```

---

### Task 1: Project scaffold + pyproject.toml

**Files:**
- Create: `pyproject.toml`
- Create: `src/ppt_agent/__init__.py`
- Create: `src/ppt_agent/__main__.py`
- Create: `tests/__init__.py`
- Create: `tests/fixtures/minimal_template.pptx`

- [ ] **Step 1: Write pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "ppt-agent"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "click>=8.1",
    "rich>=13.0",
    "pydantic>=2.5",
    "python-pptx>=0.6",
    "pyyaml>=6.0",
    "openai>=1.0",
    "anthropic>=0.30",
]

[project.scripts]
ppt-agent = "ppt_agent.cli:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Create __init__.py and __main__.py**

```python
# src/ppt_agent/__init__.py
"""PPT Agent: Professional technical solution presentation generator."""
```

```python
# src/ppt_agent/__main__.py
from .cli import main
main()
```

- [ ] **Step 3: Create test __init__.py and verify install**

```python
# tests/__init__.py
```

Run: `pip install -e .` (within the project root)
Expected: package installs without error

- [ ] **Step 4: Verify CLI entry**

Run: `python -m ppt_agent --help`
Expected: prints help (even if minimal — click not wired yet, will error, but package import works)

- [ ] **Step 5: Generate minimal template fixture**

Create `tests/fixtures/minimal_template.pptx` via a python script:

```python
# run once to generate
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
# Add a blank slide layout
blank_layout = prs.slide_layouts[6]
slide = prs.slides.add_slide(blank_layout)
# Add a title box to establish placeholder
from pptx.util import Emu
left = Emu(685800)
top = Emu(274638)
width = Emu(13716000)
height = Emu(1371600)
txBox = slide.shapes.add_textbox(left, top, width, height)
tf = txBox.text_frame
tf.text = "Test"
prs.save("tests/fixtures/minimal_template.pptx")
print("Created minimal_template.pptx")
```

Run the script from project root to generate the fixture.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/ tests/
git commit -m "feat: project scaffold with pyproject.toml and package structure"
```

---

### Task 2: Pydantic models

**Files:**
- Create: `src/ppt_agent/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_models.py
import pytest
from pydantic import ValidationError
from ppt_agent.models import (
    ArchNode, ArchEdge, ArchDiagram,
    SlideContent, SlideFramework, PPTFramework
)


class TestArchDiagram:
    def test_node_creation(self):
        node = ArchNode(id="app", label="应用层", style="group")
        assert node.id == "app"
        assert node.label == "应用层"
        assert node.children == []

    def test_node_invalid_style(self):
        with pytest.raises(ValidationError):
            ArchNode(id="x", label="x", style="invalid")

    def test_edge_creation(self):
        edge = ArchEdge(from_id="app", to_id="db", label="gRPC")
        assert edge.from_id == "app"
        assert edge.to_id == "db"

    def test_diagram_creation(self):
        diag = ArchDiagram(
            type="layered",
            nodes=[
                ArchNode(id="app", label="应用层", children=["web", "api"]),
                ArchNode(id="data", label="数据层"),
            ],
            edges=[ArchEdge(from_id="app", to_id="data")],
        )
        assert diag.type == "layered"
        assert len(diag.nodes) == 2


class TestSlideFramework:
    def test_slide_content(self):
        slide = SlideContent(
            title="架构总览",
            slide_type="arch_diagram",
            diagram=ArchDiagram(
                type="layered", nodes=[ArchNode(id="a", label="A")], edges=[]
            ),
        )
        assert slide.title == "架构总览"

    def test_slide_text_content(self):
        slide = SlideContent(
            title="背景与痛点",
            slide_type="text",
            bullets=["痛点1", "痛点2", "痛点3"],
        )
        assert len(slide.bullets) == 3

    def test_framework_creation(self):
        fw = SlideFramework(slides=[SlideContent(title="封面", slide_type="title")])
        assert len(fw.slides) == 1

    def test_ppt_framework(self):
        ppt = PPTFramework(
            title="AI训练平台方案",
            framework=SlideFramework(slides=[
                SlideContent(title="封面", slide_type="title"),
            ]),
        )
        assert ppt.title == "AI训练平台方案"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py -v`
Expected: ModuleNotFoundError / ImportError (models.py doesn't exist yet)

- [ ] **Step 3: Write the models**

```python
# src/ppt_agent/models.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_models.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/ppt_agent/models.py tests/test_models.py
git commit -m "feat: add pydantic models for arch diagrams and slide framework"
```

---

### Task 3: Config system + Session management

**Files:**
- Create: `src/ppt_agent/config.py`
- Create: `src/ppt_agent/session.py`
- Create: `tests/test_config.py`
- Create: `tests/test_session.py`

- [ ] **Step 1: Write config tests**

```python
# tests/test_config.py
import os
import tempfile
import yaml
from ppt_agent.config import Config, load_config


class TestConfig:
    def test_default_config(self):
        cfg = Config()
        assert cfg.llm.default_provider == "openai"

    def test_config_with_template(self):
        cfg = Config(template_path="/path/to/template.pptx")
        assert cfg.template_path == "/path/to/template.pptx"

    def test_load_config_from_file(self):
        data = {
            "llm": {
                "default_provider": "anthropic",
                "providers": {
                    "anthropic": {"api_key": "sk-test"},
                },
            }
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(data, f)
            f.flush()
            cfg = load_config(f.name)
            assert cfg.llm.default_provider == "anthropic"
            assert cfg.llm.providers["anthropic"].api_key == "sk-test"
        os.unlink(f.name)
```

- [ ] **Step 2: Write session tests**

```python
# tests/test_session.py
import json
import tempfile
from pathlib import Path
from ppt_agent.session import Session


class TestSession:
    def test_session_creation(self):
        session = Session(topic="AI训练平台")
        assert session.topic == "AI训练平台"
        assert session.session_id is not None
        assert len(session.messages) == 0

    def test_add_message(self):
        session = Session(topic="test")
        session.add_message("user", "你好")
        assert len(session.messages) == 1
        assert session.messages[0]["role"] == "user"

    def test_save_and_load(self, tmp_path):
        session = Session(topic="test", session_dir=str(tmp_path))
        session.add_message("user", "你好")
        session.add_message("assistant", "请说")
        path = session.save()
        loaded = Session.load(path)
        assert loaded.topic == "test"
        assert len(loaded.messages) == 2
        assert loaded.messages[1]["content"] == "请说"
```

- [ ] **Step 3: Run tests to verify failure**

Run: `pytest tests/test_config.py tests/test_session.py -v`
Expected: ImportError / ModuleNotFoundError

- [ ] **Step 4: Write config module**

```python
# src/ppt_agent/config.py
from __future__ import annotations
from pathlib import Path
import yaml
from pydantic import BaseModel


class LLMProviderConfig(BaseModel):
    api_key: str = ""
    fast_model: str = "gpt-4o-mini"
    deep_model: str = "o3"


class LLMConfig(BaseModel):
    default_provider: str = "openai"
    providers: dict[str, LLMProviderConfig] = {
        "openai": LLMProviderConfig(),
        "anthropic": LLMProviderConfig(
            fast_model="claude-sonnet-4-20250514",
            deep_model="claude-thinking-4-20250514",
        ),
    }
    routing: dict[str, str] = {
        "daily_chat": "fast",
        "deep_reasoning": "deep",
        "adversarial": "dual",
    }


class Config(BaseModel):
    template_path: str = ""
    llm: LLMConfig = LLMConfig()


def load_config(path: str | None = None) -> Config:
    if path is None:
        config_dir = Path.home() / ".ppt-agent"
        path = str(config_dir / "config.yaml")
    config_path = Path(path)
    if config_path.exists():
        with open(config_path) as f:
            data = yaml.safe_load(f)
        return Config.model_validate(data)
    return Config()
```

- [ ] **Step 5: Write session module**

```python
# src/ppt_agent/session.py
from __future__ import annotations
import json
import uuid
from datetime import datetime
from pathlib import Path


class Session:
    def __init__(self, topic: str, session_dir: str | None = None):
        self.session_id = str(uuid.uuid4())[:8]
        self.topic = topic
        self.created_at = datetime.now().isoformat()
        self.messages: list[dict] = []
        self.framework: dict | None = None
        self.session_dir = session_dir or str(Path.home() / ".ppt-agent" / "sessions")

    def add_message(self, role: str, content: str, metadata: dict | None = None):
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            **(metadata or {}),
        })

    def save(self) -> str:
        path = Path(self.session_dir) / f"{self.created_at[:10]}_{self.session_id}"
        path.mkdir(parents=True, exist_ok=True)
        file_path = path / "session.json"
        with open(file_path, "w") as f:
            json.dump({
                "session_id": self.session_id,
                "topic": self.topic,
                "created_at": self.created_at,
                "messages": self.messages,
                "framework": self.framework,
            }, f, ensure_ascii=False, indent=2)
        return str(file_path)

    @classmethod
    def load(cls, path: str) -> Session:
        with open(path) as f:
            data = json.load(f)
        session = cls(topic=data["topic"])
        session.session_id = data["session_id"]
        session.created_at = data["created_at"]
        session.messages = data["messages"]
        session.framework = data.get("framework")
        return session
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_config.py tests/test_session.py -v`
Expected: all tests pass

- [ ] **Step 7: Commit**

```bash
git add src/ppt_agent/config.py src/ppt_agent/session.py tests/test_config.py tests/test_session.py
git commit -m "feat: add config loader and session management"
```

---

### Task 4: CLI entry point + commands

**Files:**
- Create: `src/ppt_agent/cli.py`

- [ ] **Step 1: Write CLI test**

```python
# Append to existing test imports or add inline... 
# For CLI we test via click's CliRunner
```

Since click testing requires the full orchestrator, this task focuses on wiring the CLI skeleton. Full end-to-end test comes in Task 10.

- [ ] **Step 2: Write CLI module**

```python
# src/ppt_agent/cli.py
import click
from pathlib import Path


@click.group()
@click.option("--config", "-c", default=None, help="Config file path")
@click.pass_context
def cli(ctx, config):
    """PPT Agent — Professional technical presentation generator."""
    ctx.ensure_object(dict)
    from ppt_agent.config import load_config
    ctx.obj["config"] = load_config(config)


@cli.command()
@click.argument("topic")
@click.option("--template", "-t", default=None, help="Path to .pptx template")
@click.option("--model", "-m", default=None, help="LLM model override")
@click.pass_context
def new(ctx, topic, template, model):
    """Start a new PPT project."""
    from ppt_agent.orchestrator import run_new_project
    run_new_project(
        topic=topic,
        config=ctx.obj["config"],
        template_path=template,
        model_override=model,
    )


@cli.command()
@click.argument("session_path")
@click.pass_context
def resume(ctx, session_path):
    """Resume an existing session."""
    from ppt_agent.orchestrator import run_resume_session
    run_resume_session(session_path=session_path, config=ctx.obj["config"])


@cli.command("list")
@click.pass_context
def list_sessions(ctx):
    """List all saved sessions."""
    from ppt_agent.session import Session
    sessions_dir = Path.home() / ".ppt-agent" / "sessions"
    if not sessions_dir.exists():
        click.echo("No sessions found.")
        return
    for session_dir in sorted(sessions_dir.iterdir()):
        session_file = session_dir / "session.json"
        if session_file.exists():
            session = Session.load(str(session_file))
            click.echo(f"  {session.created_at[:10]} [{session.session_id}] {session.topic}")


def main():
    cli(obj={})


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Verify CLI works**

Run: `python -m ppt_agent --help`
Expected: shows help with new, resume, list commands

Run: `python -m ppt_agent list`
Expected: "No sessions found."

- [ ] **Step 4: Commit**

```bash
git add src/ppt_agent/cli.py
git commit -m "feat: add CLI entry with new/resume/list commands"
```

---

### Task 5: LLM integration (providers + router)

**Files:**
- Create: `src/ppt_agent/llm/__init__.py`
- Create: `src/ppt_agent/llm/base.py`
- Create: `src/ppt_agent/llm/openai_provider.py`
- Create: `src/ppt_agent/llm/anthropic_provider.py`
- Create: `src/ppt_agent/llm/router.py`

- [ ] **Step 1: Write provider interface and router tests**

```python
# tests/test_llm.py
from ppt_agent.llm.base import LLMProvider
from ppt_agent.llm.router import ModelRouter
from ppt_agent.config import Config


class TestModelRouter:
    def test_router_creation(self):
        router = ModelRouter(Config())
        assert router is not None

    def test_get_model_for_daily(self):
        router = ModelRouter(Config())
        provider, model = router.get_model("daily_chat")
        assert provider is not None
        assert model is not None
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_llm.py -v`
Expected: ModuleNotFoundError

- [ ] **Step 3: Write base provider**

```python
# src/ppt_agent/llm/__init__.py
```

```python
# src/ppt_agent/llm/base.py
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    def chat(self, messages: list[dict], model: str = "", **kwargs) -> str:
        ...

    @abstractmethod
    def chat_structured(self, messages: list[dict], response_model: type, model: str = "", **kwargs) -> object:
        ...
```

- [ ] **Step 4: Write OpenAI provider**

```python
# src/ppt_agent/llm/openai_provider.py
from openai import OpenAI
from ppt_agent.llm.base import LLMProvider


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str = ""):
        self.client = OpenAI(api_key=api_key if api_key else None)

    def chat(self, messages: list[dict], model: str = "gpt-4o-mini", **kwargs) -> str:
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs,
        )
        return response.choices[0].message.content or ""

    def chat_structured(self, messages: list[dict], response_model: type, model: str = "gpt-4o-mini", **kwargs) -> object:
        response = self.client.beta.chat.completions.parse(
            model=model,
            messages=messages,
            response_format=response_model,
            **kwargs,
        )
        return response.choices[0].message.parsed
```

- [ ] **Step 5: Write Anthropic provider**

```python
# src/ppt_agent/llm/anthropic_provider.py
from anthropic import Anthropic
from ppt_agent.llm.base import LLMProvider


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str = ""):
        self.client = Anthropic(api_key=api_key if api_key else None)

    def chat(self, messages: list[dict], model: str = "claude-sonnet-4-20250514", **kwargs) -> str:
        system = ""
        filtered_messages = []
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            else:
                filtered_messages.append({"role": m["role"], "content": m["content"]})
        response = self.client.messages.create(
            model=model,
            system=system or None,
            messages=filtered_messages,
            **kwargs,
        )
        return response.content[0].text

    def chat_structured(self, messages: list[dict], response_model: type, model: str = "claude-sonnet-4-20250514", **kwargs) -> object:
        result = self.chat(messages, model, **kwargs)
        return response_model.model_validate_json(result)
```

- [ ] **Step 6: Write model router**

```python
# src/ppt_agent/llm/router.py
from ppt_agent.config import Config, LLMProviderConfig
from ppt_agent.llm.base import LLMProvider
from ppt_agent.llm.openai_provider import OpenAIProvider
from ppt_agent.llm.anthropic_provider import AnthropicProvider


class ModelRouter:
    def __init__(self, config: Config):
        self.config = config
        self._providers: dict[str, LLMProvider] = {}

    def _get_provider(self, provider_name: str) -> LLMProvider:
        if provider_name not in self._providers:
            provider_config = self.config.llm.providers.get(provider_name)
            if not provider_config:
                raise ValueError(f"Unknown provider: {provider_name}")
            if provider_name == "openai":
                self._providers[provider_name] = OpenAIProvider(provider_config.api_key)
            elif provider_name == "anthropic":
                self._providers[provider_name] = AnthropicProvider(provider_config.api_key)
            else:
                raise ValueError(f"Unsupported provider: {provider_name}")
        return self._providers[provider_name]

    def get_model(self, route: str) -> tuple[LLMProvider, str]:
        """Get provider and model for a route key."""
        tier = self.config.llm.routing.get(route, "fast")
        provider_name = self.config.llm.default_provider
        provider_config = self.config.llm.providers[provider_name]
        model = provider_config.deep_model if tier == "deep" else provider_config.fast_model
        return self._get_provider(provider_name), model
```

- [ ] **Step 7: Run tests**

Run: `pytest tests/test_llm.py -v`
Expected: all pass

- [ ] **Step 8: Commit**

```bash
git add src/ppt_agent/llm/ tests/test_llm.py
git commit -m "feat: add LLM providers (OpenAI + Anthropic) and model router"
```

---

### Task 6: Template analyzer

**Files:**
- Create: `src/ppt_agent/template/__init__.py`
- Create: `src/ppt_agent/template/analyzer.py`
- Create: `tests/test_template_analyzer.py`

- [ ] **Step 1: Write template analyzer test**

```python
# tests/test_template_analyzer.py
from pathlib import Path
from ppt_agent.template.analyzer import TemplateInfo, analyze_template


class TestTemplateAnalyzer:
    def test_analyze_minimal(self):
        fixture = Path(__file__).parent / "fixtures" / "minimal_template.pptx"
        info = analyze_template(str(fixture))
        assert isinstance(info, TemplateInfo)
        assert info.slide_width > 0
        assert info.slide_height > 0

    def test_template_missing_file(self):
        import pytest
        with pytest.raises(FileNotFoundError):
            analyze_template("/nonexistent.pptx")
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_template_analyzer.py -v`
Expected: ModuleNotFoundError

- [ ] **Step 3: Write template analyzer**

```python
# src/ppt_agent/template/__init__.py
```

```python
# src/ppt_agent/template/analyzer.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from pptx import Presentation
from pptx.util import Emu


@dataclass
class FontInfo:
    major: str = "Calibri"
    minor: str = "Calibri"


@dataclass
class ColorScheme:
    accent1: str = "4472C4"
    accent2: str = "ED7D31"
    accent3: str = "70AD47"
    accent4: str = "FFC000"
    dark1: str = "000000"
    dark2: str = "44546A"
    light1: str = "FFFFFF"
    light2: str = "F2F2F2"


@dataclass
class TemplateInfo:
    slide_width: int
    slide_height: int
    color_scheme: ColorScheme
    font: FontInfo
    logo_path: str | None = None
    background_style: str = "solid"


def analyze_template(path: str) -> TemplateInfo:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Template not found: {path}")
    prs = Presentation(path)
    width = prs.slide_width
    height = prs.slide_height
    scheme = ColorScheme()
    font = FontInfo()
    # Try to extract theme colors and fonts from slide master
    for master in prs.slide_masters:
        if hasattr(master, 'slide_layouts'):
            pass
        # For now we rely on python-pptx's limited theme API;
        # more detailed extraction via lxml parsing can be added later.
    logo_path = None
    # Check first slide for images that could be logos
    if prs.slides:
        for shape in prs.slides[0].shapes:
            if shape.shape_type == 13:  # Picture
                # Extract image to temp for reference
                logo_path = f"extracted_logo_{shape.shape_id}.png"
    return TemplateInfo(
        slide_width=width,
        slide_height=height,
        color_scheme=scheme,
        font=font,
        logo_path=logo_path,
    )
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_template_analyzer.py -v`
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add src/ppt_agent/template/ tests/test_template_analyzer.py
git commit -m "feat: add .pptx template analyzer"
```

---

### Task 7: Shape renderer + quality check

**Files:**
- Create: `src/ppt_agent/generator/__init__.py`
- Create: `src/ppt_agent/generator/shape_renderer.py`
- Create: `src/ppt_agent/generator/quality_check.py`
- Create: `tests/test_shape_renderer.py`
- Create: `tests/test_quality_check.py`

- [ ] **Step 1: Write quality check tests**

```python
# tests/test_quality_check.py
from ppt_agent.generator.quality_check import (
    check_overlap, check_slide_bounds, check_font_size, score_quality
)
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor


class TestQualityCheck:
    def test_no_overlap(self):
        prs = Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        left = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(3), Inches(1))
        right = slide.shapes.add_textbox(Inches(5), Inches(1), Inches(3), Inches(1))
        overlaps = check_overlap(slide)
        assert len(overlaps) == 0

    def test_has_overlap(self):
        prs = Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        a = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(4), Inches(2))
        b = slide.shapes.add_textbox(Inches(2), Inches(1.5), Inches(4), Inches(2))
        overlaps = check_overlap(slide)
        assert len(overlaps) > 0

    def test_within_bounds(self):
        prs = Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        s = slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(5), Inches(3))
        violations = check_slide_bounds(slide, prs.slide_width, prs.slide_height)
        assert len(violations) == 0

    def test_out_of_bounds(self):
        prs = Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        s = slide.shapes.add_textbox(Inches(12), Inches(0), Inches(5), Inches(3))
        violations = check_slide_bounds(slide, prs.slide_width, prs.slide_height)
        assert len(violations) > 0

    def test_score_perfect(self):
        prs = Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        slide.shapes.add_textbox(Inches(1), Inches(1), Inches(3), Inches(1))
        score = score_quality(slide, prs.slide_width, prs.slide_height)
        assert score == 100

    def test_score_with_overlap(self):
        prs = Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        a = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(4), Inches(2))
        b = slide.shapes.add_textbox(Inches(2), Inches(1.5), Inches(4), Inches(2))
        score = score_quality(slide, prs.slide_width, prs.slide_height)
        assert score < 100
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/test_quality_check.py -v`
Expected: ModuleNotFoundError

- [ ] **Step 3: Write quality check module**

```python
# src/ppt_agent/generator/quality_check.py
from pptx import Presentation
from pptx.util import Emu


def _shape_bounds(shape):
    """Get (left, top, right, bottom) in EMU."""
    return (
        shape.left,
        shape.top,
        shape.left + shape.width,
        shape.top + shape.height,
    )


def _rects_overlap(a, b):
    """Check if two axis-aligned rectangles overlap."""
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def check_overlap(slide) -> list[tuple]:
    """Return list of overlapping shape index pairs."""
    shapes = list(slide.shapes)
    if not hasattr(slide, '_shapes_cache'):
        pass
    overlaps = []
    rects = [_shape_bounds(s) for s in shapes]
    for i in range(len(shapes)):
        for j in range(i + 1, len(shapes)):
            if _rects_overlap(rects[i], rects[j]):
                overlaps.append((i, j))
    return overlaps


def check_slide_bounds(slide, slide_width: int, slide_height: int) -> list[str]:
    """Return shapes that exceed slide boundaries."""
    violations = []
    for shape in slide.shapes:
        if (shape.left < 0 or shape.top < 0 or
                shape.left + shape.width > slide_width or
                shape.top + shape.height > slide_height):
            violations.append(str(shape))
    return violations


def check_font_size(slide, min_pt: int = 8) -> list[str]:
    """Return shapes with font size below min_pt."""
    violations = []
    for shape in slide.shapes:
        if hasattr(shape, "text_frame"):
            for para in shape.text_frame.paragraphs:
                for run in para.runs:
                    if run.font.size and run.font.size < min_pt * 12700:
                        violations.append(str(run))
    return violations


def score_quality(slide, slide_width: int, slide_height: int) -> int:
    """Score 0-100. Below 60 triggers Image Fallback."""
    score = 100
    overlaps = check_overlap(slide)
    if overlaps:
        score -= min(40, len(overlaps) * 20)
    bounds_violations = check_slide_bounds(slide, slide_width, slide_height)
    if bounds_violations:
        score -= min(30, len(bounds_violations) * 15)
    font_violations = check_font_size(slide)
    if font_violations:
        score -= min(20, len(font_violations) * 5)
    return max(score, 0)
```

- [ ] **Step 4: Run quality check tests**

Run: `pytest tests/test_quality_check.py -v`
Expected: all pass

- [ ] **Step 5: Write shape renderer test**

```python
# tests/test_shape_renderer.py
from ppt_agent.models import ArchDiagram, ArchNode, ArchEdge
from ppt_agent.generator.shape_renderer import (
    layout_layered, layout_flow, layout_radial, layout_grid,
    render_diagram_to_slide,
)
from ppt_agent.template.analyzer import TemplateInfo, ColorScheme, FontInfo
from pptx import Presentation
from pptx.util import Inches


class TestShapeRenderer:
    def test_layout_layered(self):
        diag = ArchDiagram(
            type="layered",
            nodes=[
                ArchNode(id="app", label="应用层", children=["web", "api"]),
                ArchNode(id="data", label="数据层"),
            ],
            edges=[ArchEdge(from_id="app", to_id="data")],
        )
        positions = layout_layered(diag)
        assert "app" in positions
        assert positions["app"]["y"] < positions["data"]["y"]

    def test_render_to_slide(self):
        prs = Presentation()
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        diag = ArchDiagram(
            type="layered",
            nodes=[ArchNode(id="a", label="A"), ArchNode(id="b", label="B")],
            edges=[ArchEdge(from_id="a", to_id="b")],
        )
        template = TemplateInfo(
            slide_width=prs.slide_width,
            slide_height=prs.slide_height,
            color_scheme=ColorScheme(),
            font=FontInfo(),
        )
        render_diagram_to_slide(slide, diag, template)
        assert len(slide.shapes) > 0
```

- [ ] **Step 6: Run shape renderer tests (fail first)**

Run: `pytest tests/test_shape_renderer.py -v`
Expected: ImportError

- [ ] **Step 7: Write shape renderer**

```python
# src/ppt_agent/generator/shape_renderer.py
from __future__ import annotations
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

from ppt_agent.models import ArchDiagram, ArchNode, ArchEdge
from ppt_agent.template.analyzer import TemplateInfo


def _hex_to_rgb(hex_color: str) -> RGBColor:
    h = hex_color.lstrip("#")
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def layout_layered(diag: ArchDiagram) -> dict[str, dict]:
    """Top-to-bottom layered layout for arch diagrams."""
    positions = {}
    # Assign layers: group nodes on top, their children below
    group_nodes = {n.id: n for n in diag.nodes if n.style == "group"}
    component_nodes = {n.id: n for n in diag.nodes if n.style != "group"}
    y_offset = Emu(500000)
    for gid, gnode in group_nodes.items():
        positions[gid] = {"x": Emu(1000000), "y": y_offset, "w": Emu(11000000), "h": Emu(600000)}
        y_offset += Emu(900000)
    for cid in component_nodes:
        positions[cid] = {"x": Emu(1000000), "y": y_offset, "w": Emu(11000000), "h": Emu(500000)}
        y_offset += Emu(800000)
    # Ensure all nodes have positions
    for node in diag.nodes:
        if node.id not in positions:
            positions[node.id] = {"x": Emu(1000000), "y": y_offset, "w": Emu(2500000), "h": Emu(500000)}
            y_offset += Emu(700000)
    return positions


def layout_flow(diag: ArchDiagram) -> dict[str, dict]:
    """Left-to-right flow layout."""
    positions = {}
    x_offset = Emu(500000)
    for node in diag.nodes:
        positions[node.id] = {
            "x": x_offset,
            "y": Emu(2000000),
            "w": Emu(2500000),
            "h": Emu(1000000),
        }
        x_offset += Emu(3000000)
    return positions


def layout_radial(diag: ArchDiagram) -> dict[str, dict]:
    """Simple radial layout (center + surrounding)."""
    positions = {}
    cx = Emu(6500000)
    cy = Emu(3500000)
    if diag.nodes:
        center = diag.nodes[0]
        positions[center.id] = {"x": cx - Emu(1000000), "y": cy - Emu(350000), "w": Emu(2000000), "h": Emu(700000)}
        angle_step = 360 / max(len(diag.nodes) - 1, 1)
        for i, node in enumerate(diag.nodes[1:], 1):
            import math
            rad = math.radians(i * angle_step)
            rx = int(cx + Emu(2500000) * math.cos(rad) - Emu(1000000))
            ry = int(cy + Emu(2000000) * math.sin(rad) - Emu(300000))
            positions[node.id] = {"x": rx, "y": ry, "w": Emu(2000000), "h": Emu(600000)}
    return positions


def layout_grid(diag: ArchDiagram) -> dict[str, dict]:
    """Grid layout for equal-sized boxes."""
    positions = {}
    cols = 3
    cell_w = Emu(3800000)
    cell_h = Emu(1500000)
    start_x = Emu(500000)
    start_y = Emu(1000000)
    for i, node in enumerate(diag.nodes):
        col = i % cols
        row = i // cols
        positions[node.id] = {
            "x": start_x + col * cell_w,
            "y": start_y + row * cell_h,
            "w": cell_w - Emu(200000),
            "h": cell_h - Emu(200000),
        }
    return positions


def _get_layout_func(diagram_type: str):
    return {
        "layered": layout_layered,
        "flow": layout_flow,
        "radial": layout_radial,
        "grid": layout_grid,
    }.get(diagram_type, layout_layered)


def render_diagram_to_slide(slide, diag: ArchDiagram, template: TemplateInfo):
    """Render an ArchDiagram onto a slide using python-pptx shapes."""
    layout_func = _get_layout_func(diag.type)
    positions = layout_func(diag)
    accent = _hex_to_rgb(template.color_scheme.accent1)
    dark = _hex_to_rgb(template.color_scheme.dark1)
    light = _hex_to_rgb(template.color_scheme.light1)
    # Build lookups
    node_map = {n.id: n for n in diag.nodes}
    for node in diag.nodes:
        pos = positions.get(node.id)
        if not pos:
            continue
        shape = slide.shapes.add_shape(
            1,  # MSO_SHAPE.RECTANGLE
            pos["x"], pos["y"], pos["w"], pos["h"],
        )
        shape.fill.solid()
        if node.style == "group":
            shape.fill.fore_color.rgb = accent
            shape.line.fill.background()
        else:
            shape.fill.fore_color.rgb = light
            shape.line.color.rgb = accent
            shape.line.width = Pt(1)
        tf = shape.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = node.label
        p.font.size = Pt(12)
        p.font.color.rgb = light if node.style == "group" else dark
        p.alignment = PP_ALIGN.CENTER
    for edge in diag.edges:
        from_pos = positions.get(edge.from_id)
        to_pos = positions.get(edge.to_id)
        if not from_pos or not to_pos:
            continue
        # Simple connector: arrow from center-bottom of from to center-top of to
        from_cx = from_pos["x"] + from_pos["w"] // 2
        from_cy = from_pos["y"] + from_pos["h"]
        to_cx = to_pos["x"] + to_pos["w"] // 2
        to_cy = to_pos["y"]
        # python-pptx doesn't natively support arrows as connectors in the simple API.
        # We draw a thin rectangle as a line approximation.
        import math
        dx = to_cx - from_cx
        dy = to_cy - from_cy
        length = int(math.sqrt(dx * dx + dy * dy))
        if length == 0:
            continue
        angle = math.degrees(math.atan2(dy, dx))
        # Use a freeform/line shape
        connector = slide.shapes.add_shape(
            1, from_cx, from_cy, Emu(int(length * 0.8)), Emu(6000),
        )
        connector.fill.solid()
        connector.fill.fore_color.rgb = accent
        connector.line.fill.background()
        # Rotate to match direction
        from pptx.oxml.ns import qn
        sp = connector._element
        spPr = sp.find(qn('a:spPr')) if sp.find(qn('a:spPr')) is not None else sp.find(qn('p:spPr'))
        if spPr is not None:
            xfrm = spPr.find(qn('a:xfrm'))
            if xfrm is not None:
                xfrm.set('rot', str(int(angle * 60000)))
```

- [ ] **Step 8: Run shape renderer tests**

Run: `pytest tests/test_shape_renderer.py -v`
Expected: all pass (layout tests; image rendering may need visual verification)

- [ ] **Step 9: Commit**

```bash
git add src/ppt_agent/generator/ tests/test_shape_renderer.py tests/test_quality_check.py
git commit -m "feat: add shape renderer and quality self-check"
```

---

### Task 8: Image fallback

**Files:**
- Create: `src/ppt_agent/generator/image_fallback.py`

- [ ] **Step 1: Write image fallback**

```python
# src/ppt_agent/generator/image_fallback.py
from __future__ import annotations
import subprocess
import tempfile
from pathlib import Path
from pptx.util import Inches
from ppt_agent.models import ArchDiagram


def _diagram_to_mermaid(diag: ArchDiagram) -> str:
    """Convert ArchDiagram to Mermaid flowchart syntax."""
    lines = ["graph TB"]
    # Add nodes
    for node in diag.nodes:
        style = "box" if node.style == "component" else "subgraph"
        shape = "[" if node.style == "component" else "["
        if node.children:
            lines.append(f"    subgraph {node.id}[{node.label}]")
            for child in node.children:
                lines.append(f"        {child}[[{child}]]")
            lines.append("    end")
        else:
            lines.append(f"    {node.id}{{{node.label}}}")
    # Add edges
    for edge in diag.edges:
        style = "-.->" if edge.style == "dashed" else "-->"
        label = f"|{edge.label}|" if edge.label else ""
        lines.append(f"    {edge.from_id} {style}|{label}| {edge.to_id}")
    return "\n".join(lines)


def render_as_image(diag: ArchDiagram, output_path: str) -> str:
    """Render ArchDiagram as PNG using Mermaid CLI.

    Returns path to generated PNG. Falls back to a placeholder if mermaid-cli unavailable.
    """
    mermaid_code = _diagram_to_mermaid(diag)
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".mmd", delete=False) as f:
            f.write(mermaid_code)
            mmd_path = f.name
        svg_path = mmd_path.replace(".mmd", ".svg")
        png_path = mmd_path.replace(".mmd", ".png")
        subprocess.run(
            ["mmdc", "-i", mmd_path, "-o", svg_path, "-w", "1200", "-H", "675"],
            capture_output=True, timeout=30,
        )
        # mmdc can output SVG; convert to PNG if needed
        if Path(svg_path).exists() and not Path(png_path).exists():
            import cairosvg  # optional dependency
            cairosvg.svg2png(url=svg_path, write_to=png_path)
        if Path(png_path).exists():
            import shutil
            shutil.move(png_path, output_path)
            return output_path
    except (subprocess.TimeoutExpired, FileNotFoundError, ImportError):
        pass
    # Fallback: create a minimal placeholder image
    _create_placeholder_png(output_path)
    return output_path


def _create_placeholder_png(path: str):
    """Create a simple placeholder PNG when Mermaid render is unavailable."""
    try:
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (1200, 675), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.text((50, 300), "Architecture Diagram\n(Install mermaid-cli for rendering)", fill=(100, 100, 100))
        img.save(path)
    except ImportError:
        pass
```

- [ ] **Step 2: Commit**

```bash
git add src/ppt_agent/generator/image_fallback.py
git commit -m "feat: add image fallback renderer with Mermaid support"
```

---

### Task 9: Slide generator (orchestrator)

**Files:**
- Create: `src/ppt_agent/generator/slide_generator.py`

- [ ] **Step 1: Write slide generator**

```python
# src/ppt_agent/generator/slide_generator.py
from __future__ import annotations
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

from ppt_agent.models import SlideContent, SlideFramework, PPTFramework
import tempfile
from ppt_agent.template.analyzer import TemplateInfo, analyze_template
from ppt_agent.generator.shape_renderer import render_diagram_to_slide
from ppt_agent.generator.image_fallback import render_as_image
from ppt_agent.generator.quality_check import score_quality

IMAGE_FALLBACK_THRESHOLD = 60


def _hex_to_rgb(hex_color: str) -> RGBColor:
    h = hex_color.lstrip("#")
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def generate_pptx(
    ppt_framework: PPTFramework,
    template_path: str,
    output_path: str = "output.pptx",
) -> str:
    """Generate a .pptx file from a framework.

    Returns the output path.
    """
    template_info = analyze_template(template_path)
    prs = Presentation(template_path)
    content_layout = prs.slide_layouts[1]  # Title and Content
    for slide_content in ppt_framework.framework.slides:
        slide = prs.slides.add_slide(content_layout)
        if slide_content.slide_type == "title":
            _render_title_slide(slide, slide_content, template_info)
        elif slide_content.slide_type == "section_header":
            _render_section_header(slide, slide_content, template_info)
        elif slide_content.slide_type == "arch_diagram" and slide_content.diagram:
            _render_arch_slide(slide, slide_content, template_info)
        else:
            _render_text_slide(slide, slide_content, template_info)
    prs.save(output_path)
    return output_path


def _render_title_slide(slide, content: SlideContent, template: TemplateInfo):
    """Render a title slide using the template's title layout."""
    # python-pptx doesn't easily access placeholder by type reliably.
    # We clear existing content and set title text.
    for shape in slide.shapes:
        if hasattr(shape, "text_frame"):
            for para in shape.text_frame.paragraphs:
                para.text = ""
    for shape in slide.shapes:
        if hasattr(shape, "text_frame"):
            p = shape.text_frame.paragraphs[0]
            p.text = content.title
            p.font.size = Pt(28)
            p.font.color.rgb = _hex_to_rgb(template.color_scheme.dark1)
            break
    if content.notes:
        slide.notes_slide.notes_text_frame.text = content.notes


def _render_section_header(slide, content: SlideContent, template: TemplateInfo):
    _render_title_slide(slide, content, template)


def _render_text_slide(slide, content: SlideContent, template: TemplateInfo):
    for shape in slide.shapes:
        if hasattr(shape, "text_frame"):
            p = shape.text_frame.paragraphs[0]
            p.text = content.title
            p.font.size = Pt(24)
            p.font.color.rgb = _hex_to_rgb(template.color_scheme.dark1)
            break
    if content.bullets:
        # Find or create a text box for bullets
        for shape in slide.shapes:
            if hasattr(shape, "text_frame") and shape.has_text_frame:
                tf = shape.text_frame
                tf.clear()
                for i, bullet in enumerate(content.bullets):
                    if i == 0:
                        p = tf.paragraphs[0]
                    else:
                        p = tf.add_paragraph()
                    p.text = f"• {bullet}"
                    p.font.size = Pt(16)
                    p.font.color.rgb = _hex_to_rgb(template.color_scheme.dark2)
                break


def _render_arch_slide(slide, content: SlideContent, template: TemplateInfo):
    """Render architecture diagram slide. Use Shape Renderer, fallback to Image."""
    diag = content.diagram
    # Primary: use Shape Renderer
    render_diagram_to_slide(slide, diag, template)
    quality = score_quality(slide, template.slide_width, template.slide_height)
    if quality >= IMAGE_FALLBACK_THRESHOLD:
        if content.notes:
            slide.notes_slide.notes_text_frame.text = content.notes
        return
    # Fallback: remove shapes and embed image
    _clear_slide_shapes(slide)
    tmp_dir = Path(tempfile.mkdtemp())
    img_path = str(tmp_dir / "arch.png")
    render_as_image(diag, img_path)
    if Path(img_path).exists():
        slide.shapes.add_picture(img_path, Inches(1), Inches(1.5), width=Inches(11))
    if content.notes:
        slide.notes_slide.notes_text_frame.text = content.notes


def _clear_slide_shapes(slide):
    """Remove all shapes from a slide."""
    for shape in list(slide.shapes):
        sp = shape._element
        sp.getparent().remove(sp)
```

- [ ] **Step 2: Commit**

```bash
git add src/ppt_agent/generator/slide_generator.py
git commit -m "feat: add slide generator orchestrator with fallback logic"
```

---

### Task 10: Conversation orchestrator (wiring everything)

**Files:**
- Create: `src/ppt_agent/orchestrator.py`

- [ ] **Step 1: Write orchestrator**

```python
# src/ppt_agent/orchestrator.py
from __future__ import annotations
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from ppt_agent.config import Config
from ppt_agent.models import PPTFramework, SlideFramework, SlideContent
from ppt_agent.session import Session
from ppt_agent.llm.router import ModelRouter
from ppt_agent.generator.slide_generator import generate_pptx

console = Console()

SYSTEM_PROMPT = """你是PPT Agent，一个专业的技术解决方案PPT生成助手。

你的工作流程：
1. 与用户讨论PPT思路，了解背景、受众、核心论点
2. 基于讨论结果，提出清晰的slide框架（标题+每页类型+核心内容）
3. 确认框架后，生成精美的.pptx文件

风格要求：
- 逻辑清晰，抽象层次合理
- 内容精炼，避免堆砌
- 适合企业技术方案汇报场景

当前阶段：讨论阶段。请与用户深入交流，不要急于定框架。"""


def run_new_project(
    topic: str,
    config: Config,
    template_path: str | None = None,
    model_override: str | None = None,
):
    """Entry point for `ppt-agent new`."""
    session = Session(topic=topic)
    session.add_message("system", f"Topic: {topic}")
    console.print(Panel(f"[bold]开始新项目:[/bold] {topic}", style="blue"))
    if not template_path and not config.template_path:
        template_path = Prompt.ask("请输入模板 .pptx 文件路径")
    elif template_path:
        pass
    else:
        template_path = config.template_path
    router = ModelRouter(config)
    provider, model = router.get_model("daily_chat")
    # Discussion loop
    console.print(Panel("请描述你的PPT思路，我会与你讨论并帮助完善框架。输入 /done 结束讨论进入生成阶段。", style="green"))
    while True:
        user_input = Prompt.ask("[bold you]")
        if user_input.strip().lower() == "/done":
            break
        if user_input.strip().lower() == "/framework":
            _show_current_framework(session)
            continue
        session.add_message("user", user_input)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *[{"role": m["role"], "content": m["content"]} for m in session.messages[-10:]],
        ]
        with console.status("思考中..."):
            response = provider.chat(messages, model=model)
        session.add_message("assistant", response)
        console.print(Panel(response, style="yellow"))
    # Finalize framework
    console.print(Panel("正在确认最终框架...", style="blue"))
    _finalize_framework(session, provider, model)
    # Generate
    console.print(Panel("正在生成PPT...", style="blue"))
    output = generate_pptx(
        ppt_framework=session.framework,
        template_path=template_path,
    )
    session.add_message("system", f"Generated: {output}")
    session.save()
    console.print(f"[green]✅ PPT已生成: {output}[/green]")


def run_resume_session(session_path: str, config: Config):
    """Resume a previous session."""
    session = Session.load(session_path)
    console.print(Panel(f"[bold]恢复会话:[/bold] {session.topic}", style="blue"))
    router = ModelRouter(config)
    provider, model = router.get_model("daily_chat")
    for msg in session.messages[-5:]:
        role = "you" if msg["role"] == "user" else "assistant"
        console.print(f"[bold {role}:] {msg['content']}")
    # Continue discussion...
    console.print(Panel("继续讨论。输入 /done 结束讨论并重新生成。", style="green"))
    while True:
        user_input = Prompt.ask("[bold you]")
        if user_input.strip().lower() == "/done":
            break
        session.add_message("user", user_input)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *[{"role": m["role"], "content": m["content"]} for m in session.messages[-10:]],
        ]
        with console.status("思考中..."):
            response = provider.chat(messages, model=model)
        session.add_message("assistant", response)
        console.print(Panel(response, style="yellow"))
    _finalize_framework(session, provider, model)
    # Regenerate
    template_path = config.template_path
    output = generate_pptx(
        ppt_framework=session.framework,
        template_path=template_path,
    )
    session.save()
    console.print(f"[green]✅ PPT已重新生成: {output}[/green]")


def _show_current_framework(session: Session):
    if session.framework:
        for i, slide in enumerate(session.framework.framework.slides):
            console.print(f"  {i+1}. [{slide.slide_type}] {slide.title}")
    else:
        console.print("  框架尚未确定")


def _finalize_framework(session: Session, provider, model: str):
    """Use LLM to produce final structured framework from conversation history."""
    messages = [
        {"role": "system", "content": "基于对话历史，输出最终的PPT框架。必须以JSON格式输出，使用PPTFramework结构。"},
        *[{"role": m["role"], "content": m["content"]} for m in session.messages],
        {"role": "user", "content": "请输出最终的PPT框架（JSON格式，包含slides列表，每页有title, slide_type, bullets或diagram字段）"},
    ]
    with console.status("正在整理框架..."):
        response = provider.chat(messages, model=model)
    # Parse response as framework JSON
    import json
    try:
        data = json.loads(response)
        framework = PPTFramework(**data)
        session.framework = framework
        console.print("[green]框架已确认:[/green]")
        _show_current_framework(session)
    except (json.JSONDecodeError, Exception) as e:
        console.print(f"[yellow]框架解析出错，使用默认结构: {e}[/yellow]")
        # Fallback: create a minimal framework
        framework = PPTFramework(
            title=session.topic,
            framework=SlideFramework(slides=[
                SlideContent(title=session.topic, slide_type="title"),
                SlideContent(title="背景", slide_type="text", bullets=["内容待补充"]),
                SlideContent(title="方案总览", slide_type="arch_diagram"),
                SlideContent(title="总结", slide_type="text", bullets=["内容待补充"]),
            ]),
        )
        session.framework = framework
```

- [ ] **Step 2: Verify end-to-end**

Run: `python -m ppt_agent new "测试项目" --template tests/fixtures/minimal_template.pptx`
Expected: starts discussion loop, accepts input, /done triggers generation

- [ ] **Step 3: Commit**

```bash
git add src/ppt_agent/orchestrator.py
git commit -m "feat: add conversation orchestrator wiring all components"
```

---

### Self-review / Spec coverage

After implementation, run:
```bash
pytest tests/ -v
# Expected: all tests pass

python -m ppt_agent --help
# Expected: shows CLI help

python -m ppt_agent new "K8s AI训练平台" -t tests/fixtures/minimal_template.pptx
# Manual: test discussion flow, /done, verify output.pptx created
```

Then update AGENTS.md with the build/test/lint commands discovered during implementation.
