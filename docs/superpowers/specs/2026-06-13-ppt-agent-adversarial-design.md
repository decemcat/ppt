# PPT Agent — 多智能体对抗讨论设计

## 概述

子项目 3：在 PPT 框架确定前，通过多智能体对抗讨论增强逻辑严谨性。 proponents 和 critics 交叉验证，judge 综合裁决，产出更可靠框架。

## 范围

### 包含
- 多角色 Agent 定义（Proponent / Critic / Judge）
- 对抗讨论编排（多轮辩论 + 裁决）
- **人类裁决机制**：Judge 无法明确判定或双方势均力敌时，将争议点交由用户裁决
- 逻辑评分机制（对框架的逻辑性打分）
- 与 orchestrator 集成（在框架确认后、生成 PPT 前运行对抗讨论）
- CLI 控制参数（`--debate-rounds` / `--no-debate`）

### 不包含
- Research pipeline（子项目 2）
- 视觉质检（子项目 4）
- 风格学习（子项目 5）

## 架构

```
AdversarialDiscussion（入口）
  │
  ├── Proponent（辩护方）
  │   └── LLM (deep_model) → 为框架辩护，回应批评
  │
  ├── Critic（批评方）
  │   └── LLM (deep_model) → 找出逻辑漏洞、缺失视角、薄弱论点
  │
  └── Judge（裁决方）
      └── LLM (deep_model) → 综合双方观点，产出优化后的框架

调用链路：
  orchestrator._finalize_framework()
    → AdversarialDiscussion.run(framework, context)
    → 多轮辩论
    → Judge 输出优化框架
    → 用户确认
```

## 数据模型

```python
class Critique(BaseModel):
    point: str               # 批评要点
    severity: Literal["critical", "important", "minor"]
    suggestion: str          # 改进建议

class ContestedPoint(BaseModel):
    critique: Critique       # 原始批评
    defense: str             # Proponent 的辩护
    judge_verdict: Literal["accept", "reject", "undecided"]  # Judge 初步判定
    reason: str              # Judge 的理由

class DebateRound(BaseModel):
    round_number: int
    critiques: list[Critique]
    defenses: list[str]      # Proponent 的回应
    contested: list[ContestedPoint]  # 争议点
    judge_notes: str         # Judge 的观察

class DebateResult(BaseModel):
    original_framework: PPTFramework
    rounds: list[DebateRound]
    final_framework: PPTFramework
    improvements: list[str]  # 改进摘要
    logic_score: float       # 0-100，逻辑严谨性评分
    human_rulings: list[str] # 用户裁决记录
```

## 对抗讨论流程

```
1. 输入：PPTFramework + 讨论上下文

2. Round N:
   a. Critic 审查框架，输出 Critique 列表
      Prompt: "你是逻辑审查专家。审查以下PPT框架..."
   b. Proponent 回应每个 Critique
      Prompt: "你是方案辩护方。回应以下批评..."
   c. Judge 评估双方观点，记录观察
      Prompt: "你是裁判。评估批评和辩护的合理性..."

3. 终止条件（满足任一）：
   a. 达到最大轮数（默认 2）
   b. Critic 不再提出 critical 级别批评
   c. Logic score >= 85

4. 人类裁决（条件触发）：
   条件：Judge 对某个批评点的判定为 "undecided"，或
         同一批评点经两轮辩论仍无法达成共识
   流程：
   a. 展示争议点：批评 → 辩护 → Judge 的犹豫理由
   b. 询问用户："对此争议点，你倾向哪方？"
      - 接受批评（修改框架）
      - 维持原框架
      - 输入你自己的观点
   c. 用户意见作为 Judge 最终裁决的输入

5. Judge 综合所有判定（含人类裁决）输出最终优化框架

6. 展示给用户确认
```

## Prompt 设计

### Critic Prompt

```
你是PPT框架的逻辑审查专家。你的职责是找出以下技术方案PPT框架中的逻辑问题。

审查维度：
1. **逻辑连贯性**：各页之间是否有清晰的逻辑主线？是否存在跳跃或断裂？
2. **论点充分性**：核心论点是否有足够支撑？是否存在未论证的假设？
3. **视角完整性**：是否遗漏了重要相关方或关键风险？
4. **抽象层次**：抽象层次是否合理？是否有过深或过浅的问题？
5. **信息时效性**：是否依赖了可能过时的信息或技术？

框架：
{framework}

讨论上下文：
{context}

请逐项审查，输出 Critique 列表。每项标注严重程度和改进建议。
```

### Proponent Prompt

```
你是方案辩护方。针对以下对PPT框架的批评，逐一回应：

批评：
{critiques}

原始框架：
{framework}

讨论上下文：
{context}

为每个批评点辩护或承认，说明理由。如果批评合理，提出修改方案。
```

### Judge Prompt

```
你是裁判。基于以下批评和辩护，做出裁决：

批评：{critiques}
辩护：{defenses}

对每个批评点判定：
- 批评成立 → accept，纳入修改
- 批评不成立 → reject，维持原框架
- 无法判定 → undecided，需要人类裁决

当你无法明确判定时，必须标记为 undecided 并说明理由。
无法判定的情况包括：
- 双方论点都有道理，难分高下
- 缺乏足够信息做出判断
- 涉及用户特定的业务偏好或主观判断

对可判定的点，输出折中方案或修改建议。
```

### Human Ruling Prompt（CLI 交互）

```
⚠️ 争议点需要你的裁决：

📋 批评：{critique.point}
   严重程度：{critique.severity}
   建议：{critique.suggestion}

🛡️ 辩护：{defense}

⚖️ 裁判犹豫理由：{judge_reason}

请选择：
1. 接受批评（修改框架）
2. 维持原框架
3. 输入你自己的观点
```

## 逻辑评分规则

| 维度 | 权重 | 评估方式 |
|------|------|---------|
| 逻辑连贯性 | 30% | Critic 指出的断裂点数量 |
| 论点充分性 | 25% | 未支撑的核心论点数量 |
| 视角完整性 | 20% | 遗漏的关键视角数量 |
| 抽象层次合理性 | 15% | 层次过深/过浅的问题数量 |
| 时效可靠性 | 10% | 依赖过时信息的数量 |

初始 100 分，每个 critical 扣 15，important 扣 8，minor 扣 3。

## 配置

```yaml
llm:
  routing:
    adversarial: dual  # 对抗讨论使用双模型

debate:
  max_rounds: 2
  min_logic_score: 85
  enabled: true
```

## 集成点

在 `orchestrator.py` 的 `_finalize_framework` 之后，`generate_pptx` 之前：

```python
# 对抗讨论
if config.debate.enabled:
    from ppt_agent.adversarial.discussion import AdversarialDiscussion
    discussion = AdversarialDiscussion(config, router)
    debate_result = discussion.run(framework=session.framework, context=session.messages)
    session.framework = debate_result.final_framework
    console.print(f"[green]对抗讨论完成，逻辑评分: {debate_result.logic_score}/100[/green]")
```
