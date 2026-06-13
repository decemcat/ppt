# PPT Agent — Research Pipeline 设计

## 概述

子项目 2：Research 管线。自动从 Web、学术论文、GitHub 项目搜集信息，经提取后存入向量库（ChromaDB）+ 知识图谱（NetworkX/Neo4j），并提供 LLM Wiki（CLI + HTML）供浏览检索。

## 范围

### 包含
- Web 搜索与内容提取（支持 GFW 代理配置）
- 学术论文搜索（arXiv + Semantic Scholar）
- GitHub 项目分析（README + star/热度）
- ChromaDB 向量存储与语义检索
- NetworkX 本地知识图谱（JSON 序列化），预留 Neo4j 适配器
- LLM Wiki：CLI 交互（rich tree）+ HTML Web（Flask 本地服务器）
- 搜索结果时效标注（每篇记录收录时间，超期预警）

### 不包含（后续子项目）
- 多智能体对抗讨论（子项目 3）
- 视觉质检（子项目 4）
- 风格学习（子项目 5）

## 架构

```
~/.ppt-agent/knowledge/
├── web/          # 网页摘要 (JSONL + ChromaDB collections)
├── papers/       # 论文摘要 (JSONL)
├── github/       # 项目分析 (JSONL)
├── graph/        # 知识图谱 (NetworkX JSON dump)
└── wiki/         # LLM Wiki 生成的页面

ResearchManager（入口）
  │
  ├── WebSearcher（agent-reach / 直接 API + 代理配置）
  │   ├── fetch_url(url, proxy) → Markdown
  │   └── search_web(query, proxy) → list[SearchResult]
  │
  ├── PaperSearcher（arXiv API + Semantic Scholar）
  │   ├── search_papers(query) → list[Paper]
  │   └── fetch_paper_abstract(arxiv_id) → str
  │
  ├── GitHubAnalyzer（PyGithub / gh CLI）
  │   ├── search_repos(query) → list[Repo]
  │   └── analyze_repo(repo_url) → RepoAnalysis
  │
  ├── ContentIndexer（存储层）
  │   ├── ChromaDB（向量索引，语义检索）
  │   └── KnowledgeGraph（NetworkX, 实体关系）
  │
  └── WikiServer（LLM Wiki）
      ├── CLI（rich Tree + 搜索）
      └── Flask（本地 Web, graph 可视化 + 搜索 UI）

Config
  proxy:
    http: http://127.0.0.1:7890
    https: http://127.0.0.1:7890
  knowledge:
    max_age_days: 180  # 默认 6 个月后预警
    auto_summarize: true
```

## 数据模型

```python
class SearchResult(BaseModel):
    url: str
    title: str
    snippet: str
    content: str  # Markdown after extraction
    source: Literal["web", "paper", "github"]
    collected_at: datetime
    metadata: dict = {}

class Paper(SearchResult):
    arxiv_id: str
    authors: list[str]
    published: date
    citations: int = 0

class RepoAnalysis(BaseModel):
    repo: str  # owner/name
    description: str
    stars: int
    topics: list[str]
    readme_summary: str
    last_commit: datetime

class KnowledgeNode(BaseModel):
    id: str
    label: str
    type: Literal["concept", "paper", "project", "person", "tool"]
    summary: str
    sources: list[str]  # URLs

class KnowledgeEdge(BaseModel):
    source_id: str
    target_id: str
    relation: str  # "cites", "implements", "extends", "related_to"
```

## 搜索层

### WebSearcher
- 优先使用 `agent-reach` skill（已有 skill，零配置）
- 备选：直接调用 Google/Bing Search API
- 内容提取：`trafilatura` / `markdownify` → Markdown
- **代理配置**：`config.yaml` 中 `proxy` 段，所有 HTTP 请求自动走代理

```yaml
proxy:
  http: http://127.0.0.1:7890
  https: http://127.0.0.1:7890
  enabled: true  # 可开关
```

### PaperSearcher
- arXiv API：`arxiv` Python 库，搜索结果含摘要 + 作者
- Semantic Scholar API：补充引用数、影响力指标
- 摘要存入向量库时标注「论文」类型

### GitHubAnalyzer
- PyGithub：搜索仓库、获取 README
- README 摘要：通过 LLM 提取核心技术栈、解决的问题、架构特点
- 分析指标：star 数、最近 commit、issue 活跃度

## 存储层

### ChromaDB 向量库
- Collection 按来源分：`web_knowledge`, `papers`, `github_repos`
- 向量化：`sentence-transformers`（`all-MiniLM-L6-v2`，本地运行）
- 检索：语义相似度 top-k，支持过滤 source 类型

### KnowledgeGraph（NetworkX）
- 实体：概念、论文、项目、人物、工具
- 关系：引用、实现、扩展、相关
- 存储：`nx.readwrite.json_graph` 序列化为 JSON
- 检索：BFS/DFS 查找关联路径 → 形成"概念地图"供讨论使用
- Neo4j 适配器：接口抽象后可选切换

## LLM Wiki

### CLI 模式
- `ppt-agent wiki` → 打开交互式浏览
- `ppt-agent wiki search "Kubernetes GPU scheduling"` → 搜索并展示结果
- `ppt-agent wiki graph "RAG"` → 展示概念图谱路径
- 使用 `rich.Tree` 渲染目录结构

### HTML 模式
- `ppt-agent wiki --serve` → 启动 Flask 本地服务器
- 功能：
  - 搜索框（向量检索）
  - 知识图谱可视化（`vis-network` / `d3.js` 前端）
  - 每个知识条目的来源链接 + 时效标注
  - 点击节点展开关联

## 时效管理

所有知识条目存储时带 `collected_at`。逻辑：
- `max_age_days` 配置（默认 180 天）
- 搜索时优先使用未过期条目（标注缓存命中）
- 过期条目显示 `[可能过时]` 标签
- 讨论阶段 LLM 收到过期条目时 prompt 中自动标注过时风险

## 配置扩展

```yaml
knowledge:
  max_age_days: 180
  auto_summarize: true
  chroma_path: ~/.ppt-agent/knowledge/chroma/
  graph_path: ~/.ppt-agent/knowledge/graph/graph.json

proxy:
  enabled: true
  http: http://127.0.0.1:7890
  https: http://127.0.0.1:7890
```

## 与子项目 1 集成的接口

ResearchManager 被 orchestrator 调用：
```python
# 在 run_new_project 中 research 阶段
research_mgr = ResearchManager(config)
results = await research_mgr.search(topic)
# results 中包含 web/papers/github 三类
# 自动存入向量库 + 知识图谱
# 返回摘要给 orchestrator 作为讨论阶段的上下文
```
