# AGENTS.md

A Python CLI tool (`ppt`) for generating technical solution PPTs from `.pptx` templates.

## Current state

- **Python:** 3.14 (Homebrew at `/opt/homebrew/bin/python3`)
- **Package manager:** pip (editable install via `.venv`: `.venv/bin/pip install -e .`)
- **Test framework:** pytest (`.venv/bin/python -m pytest tests/ -v`)
- **Git repo** on `main`
- **Install target:** `~/.ppt-agent/` (all runtime files self-contained)

## Known commands

- `./install.sh` — one-click setup (venv + pip install + config template + PATH link)
- `.venv/bin/python -m pytest tests/ -v` — run all tests
- `.venv/bin/python -m pytest tests/test_foo.py::TestClass::test_method -v` — run single test
- `ppt --help` — CLI help (after install.sh)
- `ppt new "<topic>" --template <path>` — start new project
- `ppt new "<topic>" --template <path> --style <name>` — start with style profile
- `ppt wiki` — open LLM Wiki CLI browser
- `ppt wiki --serve` — open LLM Wiki web server (localhost:8765)

- `ppt style-extract <pptx_path>` — extract style from .pptx (defaults to "default")
- `ppt style-list` — list saved style profiles
- `ppt style-show [name]` — show style profile details (defaults to "default")

> **PEP 668:** Homebrew Python 3.14 refuses `pip install` outside a venv. Always use `.venv`.

## Architecture

```
src/ppt_agent/
├── __init__.py
├── __main__.py         # python -m ppt_agent
├── cli.py              # click commands (new/resume/list/wiki/style-extract/style-list/style-show)
├── config.py           # ~/.ppt-agent/config.yaml loader (LLM/Proxy/Knowledge/Style config)
├── models.py           # pydantic models (ArchDiagram, SlideFramework, etc.)
├── session.py          # conversation session save/load
├── orchestrator.py     # research → discuss → framework → generate flow
├── llm/                # LLM providers + router
│   ├── base.py, openai_provider.py, anthropic_provider.py, router.py
├── template/
│   └── analyzer.py     # .pptx template parser
├── generator/
│   ├── slide_generator.py   # orchestrates rendering
│   ├── shape_renderer.py    # python-pptx shape rendering
│   ├── image_fallback.py    # Mermaid→SVG→PNG fallback
│   ├── image_gen.py         # AI image generation (DALL-E / compatible API)
│   └── quality_check.py     # self-check scoring
└── research/
    ├── manager.py           # ResearchManager — orchestrates all below
    ├── models.py            # SearchResult, Paper, RepoAnalysis, KnowledgeNode/Edge
    ├── web_searcher.py      # Web search (agent-reach + proxy)
    ├── paper_searcher.py    # arXiv + Semantic Scholar
    ├── github_analyzer.py   # PyGithub + gh CLI fallback
    ├── content_extractor.py # HTML→Markdown, README summarizer
    ├── chroma_indexer.py    # ChromaDB vector storage
    ├── knowledge_graph.py   # NetworkX knowledge graph
    └── wiki.py              # LLM Wiki (CLI + Flask web)
└── adversarial/
    ├── models.py            # Critique, ContestedPoint, DebateRound, DebateResult
    ├── agents.py            # CriticAgent, ProponentAgent, JudgeAgent
    ├── discussion.py        # AdversarialDiscussion orchestrator
    └── human_ruling.py      # CLI human ruling on contested points
└── quality/
    ├── slide_capture.py     # .pptx → PNG via LibreOffice headless
    ├── vision_judge.py      # Vision LLM evaluation per slide
    └── checker.py           # VisualQualityChecker + SlideScore/VisualCheckResult
└── style/
    ├── profile.py           # StyleProfile, ColorScheme, FontProfile, LayoutRatios
    └── extractor.py         # StyleExtractor — extracts style from .pptx
```

## Config structure

```yaml
# ~/.ppt-agent/config.yaml
llm:
  default_provider: openai
  providers:
    openai:
      api_key: sk-...
      fast_model: gpt-4o-mini
      deep_model: o3
proxy:
  enabled: true
  http: http://127.0.0.1:7890
  https: http://127.0.0.1:7890
knowledge:
  max_age_days: 180
template_path: /path/to/company-template.pptx
```

## Sub-project status

1. ✅ Core engine + PPT generation — `docs/superpowers/plans/2026-06-13-ppt-agent-core-plan.md`
2. ✅ Research pipeline — `docs/superpowers/plans/2026-06-13-ppt-agent-research-plan.md`
3. ✅ Multi-agent adversarial discussion — `docs/superpowers/plans/2026-06-13-ppt-agent-adversarial-plan.md`
4. ✅ Visual quality check — `docs/superpowers/plans/2026-06-13-ppt-agent-visual-check-plan.md`
5. ✅ Style learning

## Development

New tasks should be implemented via the plan in `docs/superpowers/plans/`. Each task is reviewed (spec compliance + code quality) before the next begins.
