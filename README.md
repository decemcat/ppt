# ppt

A Python CLI tool for generating professional technical solution presentations from `.pptx` templates, powered by LLMs.

## Quick Start

```bash
# 一键安装
./install.sh

# 编辑配置，填写 API Key
vim ~/.ppt-agent/config.yaml

# 开始使用
ppt new "Kubernetes Autoscaling Architecture" --template company.pptx
```

## Features

- **Research Pipeline** — Web search, arXiv/Semantic Scholar papers, GitHub repo analysis, automatic knowledge graph construction
- **Adversarial Discussion** — Multi-agent debate (critic/proponent/judge) to improve slide logic before generation
- **Visual Quality Check** — Vision model evaluates per-slide layout, density, color, hierarchy, and cleanliness
- **Style Learning** — Extract colors, fonts, and layouts from any `.pptx` and apply as a reusable style profile
- **LLM Wiki** — CLI browser and web server (localhost:8765) to explore the research knowledge base
- **Hybrid Rendering** — Shape Renderer (python-pptx native) + Image Fallback (Mermaid→PNG) for diagrams

## Commands

| Command | Description |
|---------|-------------|
| `new "<topic>"` | Start a new PPT project |
| `resume <session>` | Resume a saved session |
| `list` | List all saved sessions |
| `wiki` | Open LLM Wiki CLI browser |
| `wiki --serve` | Start Wiki web server (localhost:8765) |
| `style-extract <pptx>` | Extract style profile from a `.pptx` |
| `style-list` | List saved style profiles |
| `style-show <name>` | Show style profile details |

### `new` options

| Option | Description |
|--------|-------------|
| `-t, --template PATH` | Path to `.pptx` template |
| `-m, --model TEXT` | LLM model override |
| `--style NAME` | Apply saved style profile |
| `--no-debate` | Skip adversarial discussion |
| `--debate-rounds N` | Number of debate rounds (default: 2) |
| `--no-visual-check` | Skip visual quality check |

## Configuration

`~/.ppt-agent/config.yaml`:

```yaml
llm:
  default_provider: openai
  providers:
    openai:
      api_key: sk-xxx
      fast_model: gpt-4o-mini
      deep_model: o3
    anthropic:
      api_key: sk-ant-xxx
      fast_model: claude-sonnet-4-20250514
      deep_model: claude-opus-4-20250514
    deepseek:                    # any OpenAI-compatible API
      api_key: sk-xxx
      base_url: https://api.deepseek.com/v1
      type: openai_compatible
      fast_model: deepseek-chat
      deep_model: deepseek-reasoner

proxy:                    # optional, for GFW
  enabled: true
  http: http://127.0.0.1:7890
  https: http://127.0.0.1:7890

knowledge:
  max_age_days: 180       # staleness warning threshold

debate:
  max_rounds: 2
  min_logic_score: 85
  enabled: true

visual_check:
  enabled: true
  threshold: 7.0          # score threshold to pass
  provider: auto           # auto uses default_provider; or name like "deepseek"
  model: ""                # override vision model (empty = use fast_model)

image_gen:                 # AI image generation (DALL-E / compatible)
  provider: auto            # uses default_provider if auto
  model: ""                 # e.g., "dall-e-3"; empty = use fast_model
  base_url: ""              # full endpoint URL; empty = https://api.openai.com/v1/images/generations

template_path: /path/to/company-template.pptx
style_path: /path/to/saved-style.yaml
```

## How It Works

```
new "Topic"
  ├── ResearchManager — web search, papers, GitHub analysis
  ├── Orchestrator — LLM-driven slide framework design
  ├── AdversarialDiscussion — multi-agent debate & human ruling
  ├── SlideGenerator — hybrid shape/image rendering
  └── VisualQualityChecker — vision model evaluation
```

## Development

```bash
# 首次设置开发环境
python3 -m venv .venv && .venv/bin/pip install -e .

# 运行测试
.venv/bin/python -m pytest tests/ -v
```

Python 3.11+ required. Uses PEP 668 compliant venv.

所有运行时文件位于 `~/.ppt-agent/`:
- `.venv/` — Python 虚拟环境
- `config.yaml` — 配置文件
- `sessions/` — 会话存档
- `knowledge/` — 知识库
- `styles/` — 风格配置

## License

MIT
