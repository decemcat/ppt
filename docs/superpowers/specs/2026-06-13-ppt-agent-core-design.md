# PPT Agent — 核心引擎 + PPT 生成设计

## 概述

一个专业的技术解决方案 PPT 生成 CLI 工具。用户提供思路，Agent 通过深入的 research、讨论、逻辑推敲后，基于公司模板生成整洁的 `.pptx` 文件。

## 子项目范围

这是整体 PPT Agent 的第一个子项目「核心引擎 + PPT 生成」，涵盖：
- CLI 入口与交互框架
- 对话编排（讨论→确认框架→生成）
- 模板解析（从 `.pptx` 模板提取配色/字体/logo）
- PPT 生成引擎（python-pptx + Image Fallback）
- 知识库目录结构（预留接口）

**不包含**（后续子项目）：
- Research 管线（网页/论文/GitHub 搜索）
- 多智能体对抗讨论
- 视觉模型质检
- 风格记忆学习

## 架构

```
PPT Agent Architecture

CLI Layer
  click + rich → 对话界面 + session 管理
      │
Conversation Orchestrator
  状态机：research → discuss → finalize → generate
  持久化到 ~/.ppt-agent/sessions/
      │
LLM Integration Layer
  Provider: OpenAI / Anthropic / Volcengine / Ollama
  Routing:  快速模型 ↔ 通用对话
            高思考模型 ↔ 架构推敲 / 对抗验证
  Output:   Pydantic models (架构图描述, slide 内容, 布局数据)
      │
Template Analyzer
  读取 .pptx → slide master → 配色 / 字体 / logo / 背景
      │
Slide Generator
  ├── Shape Renderer (python-pptx)  ← 主力
  │     架构数据 → 布局计算 → 原生形状渲染
  │     + 自检评分 → 低于阈值触发 Fallback
  │
  └── Image Fallback (Mermaid→SVG→PNG) ← 降级
        同一份架构数据 → Mermaid DSL → 图片嵌入
      │
Knowledge Base Interface (预留)
  ~/.ppt-agent/knowledge/{web,papers,github,memory}/
```

## CLI 交互流程

```
$ ppt-agent new "基于K8s的AI训练平台架构方案"

1. Research ──→ [后台自动] 收集信息（本子项目用模拟数据占位）
2. Discuss  ──→ 你↔Agent 对话迭代框架
3. Finalize ──→ 确认 slide 列表
4. Generate ──→ 基于模板生成 output.pptx
5. Quality  ──→ Shape Renderer 自检 → 评分 → 降级或警告
```

关键交互设计：
- `--resume` 支持断点续聊
- `--model` 指定模型
- `--template` 指定模板 `.pptx` 路径
- 每次 session 自动保存到 `~/.ppt-agent/sessions/`

## 模板解析

输入：公司 `.pptx` 模板文件

解析结果：
- 配色表：`theme.color_scheme`（accent1-6, dark1-2, light1-2）
- 字体：`theme.font_scheme`（major/minor font）
- Logo：从 slide master 占位图中提取图片
- 背景：slide 背景填充信息

所有生成页继承 slide master 的 theme。

## 架构图描述格式

Shape Renderer 和 Image Fallback 使用同一份结构化数据：

```python
class ArchDiagram(BaseModel):
    type: Literal["layered", "flow", "radial", "grid"]
    nodes: list[ArchNode]
    edges: list[ArchEdge]

class ArchNode(BaseModel):
    id: str
    label: str
    children: list[str] = []
    style: Literal["group", "component", "datastore"] = "component"

class ArchEdge(BaseModel):
    from_id: str
    to_id: str
    label: str = ""
    style: Literal["solid", "dashed", "arrow"] = "arrow"
```

## Shape Renderer（方案 A）

- 根据 `type` 选择布局算法（分层/流水/辐射/网格）
- 计算节点位置和尺寸，避免重叠
- 使用模板 accent color 着色层级（主模块→深色，子模块→浅色）
- 渲染圆角矩形 + 连线 + 箭头
- 文本自适应字号（自动换行 + 溢出缩小）
- 输出前自检评分

### 自检评分规则

| 检查项 | 扣分阈值 | 权重 |
|--------|---------|------|
| 节点重叠 | 任意两个 bounding box 相交 | 40 分 |
| 超出 slide 边距 | 节点超出可打印区域 | 30 分 |
| 字号 < 8pt | 任何文本字号小于 8pt | 20 分 |
| 内容溢出 | 文本框内容被截断 | 10 分 |

评分 < 60 → 触发 Image Fallback

## Image Fallback（方案 B）

- 同一份 `ArchDiagram` 数据 → 翻译为 Mermaid DSL
- Mermaid → SVG → PNG（用 mermaid-cli 或 `kroki` API）
- PNG 嵌入 slide 作为全幅图片
- 保留 slide 标题和页码等模板元素

## LLM 模型路由

配置在 `~/.ppt-agent/config.yaml`：

```yaml
llm:
  default_provider: openai
  providers:
    openai:
      api_key: ...
      fast_model: gpt-4o-mini
      deep_model: o3
    anthropic:
      api_key: ...
      fast_model: claude-sonnet-4-20250514
      deep_model: claude-thinking-4-20250514
  routing:
    daily_chat: fast  # 日常讨论用快速模型
    deep_reasoning: deep  # 架构推敲用高思考模型
    adversarial: dual  # 双模型交叉验证（子项目 3 启用）
```

## 知识库目录结构（预留）

```
~/.ppt-agent/
├── config.yaml
├── sessions/
│   └── 2026-06-13_ai-training-platform/
│       ├── conversation.jsonl
│       ├── final_framework.json
│       └── output.pptx
└── knowledge/
    ├── web/        # ← 子项目 2 实现
    ├── papers/     # ← 子项目 2 实现
    ├── github/     # ← 子项目 2 实现
    └── memory/     # ← 子项目 5 实现
```

## 约束与约定

- Python 3.11+
- 依赖：`python-pptx`, `click`, `rich`, `pydantic`, `pyyaml`
- 模板解析：纯 `python-pptx` API，不依赖 LibreOffice
- Image Fallback：优先用 `mermaid-cli`（npm 包），可选 `kroki` API
- 所有路径使用 XDG 兼容（`~/.ppt-agent/`）
- 不对 `.pptx` 做后处理（不调用 Office COM，保持跨平台）
