from __future__ import annotations
from ppt_agent.llm.base import LLMProvider
from ppt_agent.llm.router import ModelRouter
from ppt_agent.models import PPTFramework
from ppt_agent.adversarial.models import Critique, ContestedPoint


CRITIC_PROMPT = """你是PPT框架的逻辑审查专家。你的职责是找出以下技术方案PPT框架中的逻辑问题。

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

请逐项审查，以JSON数组输出Critique列表，每个元素包含point、severity（critical/important/minor）、suggestion字段。"""

PROPONENT_PROMPT = """你是方案辩护方。针对以下对PPT框架的批评，逐一回应：

批评：
{critiques}

原始框架：
{framework}

讨论上下文：
{context}

为每个批评点辩护或承认，说明理由。如果批评合理，提出修改方案。"""

JUDGE_PROMPT = """你是裁判。基于以下批评和辩护，做出裁决：

批评：{critiques}
辩护：{defenses}

对每个批评点判定：
- 批评成立 → accept，纳入修改
- 批评不成立 → reject，维持原框架
- 无法判定 → undecided，需要人类裁决

无法判定的情况包括：
- 双方论点都有道理，难分高下
- 缺乏足够信息做出判断
- 涉及用户特定的业务偏好或主观判断

以JSON数组输出ContestedPoint列表，每个元素包含：
- critique: {{point, severity, suggestion}}
- defense: 辩护摘要
- judge_verdict: accept/reject/undecided
- reason: 判定理由

然后输出judge_notes总结你的观察。"""


class CriticAgent:
    def __init__(self, provider: LLMProvider, model: str):
        self.provider = provider
        self.model = model

    def review(self, framework: PPTFramework, context: str) -> list[Critique]:
        import json
        prompt = CRITIC_PROMPT.format(
            framework=framework.model_dump_json(indent=2),
            context=context[:3000],
        )
        response = self.provider.chat(
            [{"role": "user", "content": prompt}], model=self.model,
        )
        try:
            data = json.loads(response)
            if isinstance(data, list):
                return [Critique(**c) for c in data]
            return []
        except (json.JSONDecodeError, Exception):
            return []


class ProponentAgent:
    def __init__(self, provider: LLMProvider, model: str):
        self.provider = provider
        self.model = model

    def defend(self, framework: PPTFramework, critiques: list[Critique], context: str) -> list[str]:
        critiques_text = "\n".join(f"- [{c.severity}] {c.point} (建议: {c.suggestion})" for c in critiques)
        prompt = PROPONENT_PROMPT.format(
            critiques=critiques_text,
            framework=framework.model_dump_json(indent=2),
            context=context[:3000],
        )
        response = self.provider.chat(
            [{"role": "user", "content": prompt}], model=self.model,
        )
        return [line.lstrip("- ").strip() for line in response.split("\n") if line.strip().startswith("- ")] or [response]


class JudgeAgent:
    def __init__(self, provider: LLMProvider, model: str):
        self.provider = provider
        self.model = model

    def judge(self, framework: PPTFramework, critiques: list[Critique], defenses: list[str], context: str) -> tuple[list[ContestedPoint], str]:
        import json
        critiques_text = "\n".join(f"- [{c.severity}] {c.point}" for c in critiques)
        defenses_text = "\n".join(f"- {d}" for d in defenses)
        prompt = JUDGE_PROMPT.format(
            critiques=critiques_text,
            defenses=defenses_text,
        )
        response = self.provider.chat(
            [{"role": "user", "content": prompt}], model=self.model,
        )
        contested = []
        judge_notes = ""
        try:
            data = json.loads(response)
            if isinstance(data, dict):
                contested_data = data.get("contested", data.get("points", []))
                judge_notes = data.get("judge_notes", data.get("notes", ""))
            elif isinstance(data, list):
                contested_data = data
            else:
                contested_data = []
            for cp in contested_data:
                try:
                    contested.append(ContestedPoint(**cp))
                except Exception:
                    pass
        except (json.JSONDecodeError, Exception):
            judge_notes = response
        return contested, judge_notes
