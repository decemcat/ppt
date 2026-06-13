# PPT Agent — 视觉质检设计

## 概述

子项目 4：PPT 生成后，用视觉模型对幻灯片截图进行排版/整洁性评审。与已有的 Shape Renderer 自检互补——自检检查几何问题（重叠/溢出），视觉质检评估整体观感。

## 范围

### 包含
- .pptx → 图片转换（LibreOffice headless，可选依赖）
- 视觉模型评审（GPT-4o / Claude Vision）
- 评分维度：布局平衡、文字密度、配色一致性、视觉层级、整洁度
- 质检报告输出（per-slide 评分 + 总评）
- 与 orchestrator 集成（生成后自动质检，低分告警）
- `--no-visual-check` CLI 开关

### 不包含
- 自动修复能力（仅告警，不改 PPT）
- 风格学习（子项目 5）

## 架构

```
orchestrator.run_new_project()
  → generate_pptx()
  → VisualQualityChecker.check(pptx_path)
    ├── SlideCapture.pptx_to_images() → list[str]
    └── VisionJudge.evaluate(images) → VisualCheckResult
```

## 数据模型

```python
class SlideScore(BaseModel):
    slide_index: int
    layout_balance: float      # 0-10
    text_density: float        # 0-10
    color_consistency: float   # 0-10
    visual_hierarchy: float    # 0-10
    cleanliness: float         # 0-10
    overall: float             # 0-10
    issues: list[str]

class VisualCheckResult(BaseModel):
    scores: list[SlideScore]
    total_score: float
    passed: bool
    summary: str
```

## 幻灯片截图

使用 LibreOffice headless：`soffice --headless --convert-to png --outdir <dir> <file>.pptx`

若 LibreOffice 不可用，跳过视觉质检，仅使用已有的 Shape Renderer 自检。

## 视觉评审 Prompt

```
你是PPT排版评审专家。请对以下幻灯片截图进行评审。

评分维度（0-10分）：
1. 布局平衡（layout_balance）：元素是否均衡分布？有无偏重或留白不当？
2. 文字密度（text_density）：文字量是否适中？是否过于拥挤或过于稀疏？
3. 配色一致性（color_consistency）：配色是否统一和谐？有无突兀颜色？
4. 视觉层级（visual_hierarchy）：标题/正文/图表的层级是否清晰？
5. 整洁度（cleanliness）：整体是否简洁专业？有无花哨装饰？

输出JSON：
{"layout_balance":N,"text_density":N,"color_consistency":N,"visual_hierarchy":N,"cleanliness":N,"overall":N,"issues":["问题1"]}
```

## 配置

```yaml
visual_check:
  enabled: true
  threshold: 7.0
  provider: auto
```

## 集成

在 generate_pptx() 之后调用质检，低分告警。
