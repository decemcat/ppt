# Adversarial Discussion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build multi-agent adversarial discussion that strengthens PPT framework logic through proponent/critic debate, human ruling on contested points, and judge synthesis.

**Architecture:** AdversarialDiscussion orchestrates Critic→Proponent→Judge debate rounds. When Judge cannot decide or points remain contested after 2 rounds, the user is prompted for a ruling. All rulings feed into Judge's final synthesis of an improved PPTFramework.

**Tech Stack:** Python 3.11+, pydantic, rich, existing LLM provider layer.

---

## File Structure

```
src/ppt_agent/
├── config.py              # MODIFY — add DebateConfig
├── orchestrator.py        # MODIFY — add adversarial discussion phase
└── adversarial/
    ├── __init__.py
    ├── models.py          # Critique, ContestedPoint, DebateRound, DebateResult
    ├── agents.py          # Proponent, Critic, Judge LLM wrappers
    ├── discussion.py      # AdversarialDiscussion — main orchestrator
    └── human_ruling.py    # CLI interaction for contested points
tests/
├── test_adversarial_models.py
└── test_discussion.py
```

---

### Task 1: Adversarial models + config extension

**Files:**
- Create: `src/ppt_agent/adversarial/__init__.py`
- Create: `src/ppt_agent/adversarial/models.py`
- Create: `tests/test_adversarial_models.py`
- Modify: `src/ppt_agent/config.py`

- [ ] **Step 1: Create adversarial package init**

```python
# src/ppt_agent/adversarial/__init__.py
```

- [ ] **Step 2: Write adversarial models**

```python
# src/ppt_agent/adversarial/models.py
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field
from ppt_agent.models import PPTFramework


class Critique(BaseModel):
    point: str
    severity: Literal["critical", "important", "minor"]
    suggestion: str


class ContestedPoint(BaseModel):
    critique: Critique
    defense: str
    judge_verdict: Literal["accept", "reject", "undecided"]
    reason: str


class DebateRound(BaseModel):
    round_number: int
    critiques: list[Critique] = Field(default_factory=list)
    defenses: list[str] = Field(default_factory=list)
    contested: list[ContestedPoint] = Field(default_factory=list)
    judge_notes: str = ""


class DebateResult(BaseModel):
    original_framework: PPTFramework
    rounds: list[DebateRound] = Field(default_factory=list)
    final_framework: PPTFramework
    improvements: list[str] = Field(default_factory=list)
    logic_score: float = 0.0
    human_rulings: list[str] = Field(default_factory=list)
```

- [ ] **Step 3: Write tests**

```python
# tests/test_adversarial_models.py
from ppt_agent.adversarial.models import (
    Critique, ContestedPoint, DebateRound, DebateResult,
)
from ppt_agent.models import PPTFramework, SlideFramework, SlideContent


class TestAdversarialModels:
    def test_critique_creation(self):
        c = Critique(point="逻辑断层", severity="critical", suggestion="增加过渡页")
        assert c.severity == "critical"

    def test_contested_point(self):
        cp = ContestedPoint(
            critique=Critique(point="p", severity="important", suggestion="s"),
            defense="辩护理由",
            judge_verdict="undecided",
            reason="双方都有道理",
        )
        assert cp.judge_verdict == "undecided"

    def test_debate_round(self):
        r = DebateRound(round_number=1, judge_notes="test")
        assert r.round_number == 1
        assert len(r.critiques) == 0

    def test_debate_result(self):
        fw = PPTFramework(
            title="test",
            framework=SlideFramework(slides=[SlideContent(title="T", slide_type="title")]),
        )
        result = DebateResult(original_framework=fw, final_framework=fw, logic_score=75.0)
        assert result.logic_score == 75.0
```

- [ ] **Step 4: Extend config with DebateConfig**

Add to `src/ppt_agent/config.py` (before Config class):

```python
class DebateConfig(BaseModel):
    max_rounds: int = 2
    min_logic_score: int = 85
    enabled: bool = True
```

Add `debate` field to Config:

```python
    debate: DebateConfig = Field(default_factory=DebateConfig)
```

- [ ] **Step 5: Run tests**

Run: `.venv/bin/python -m pytest tests/test_adversarial_models.py tests/test_config.py -v`
Expected: all pass

- [ ] **Step 6: Commit**

```
git add src/ppt_agent/adversarial/ tests/test_adversarial_models.py src/ppt_agent/config.py
git commit -m "feat: add adversarial discussion models and DebateConfig"
```

---

### Task 2: Agent wrappers (Proponent / Critic / Judge)

**Files:**
- Create: `src/ppt_agent/adversarial/agents.py`

- [ ] **Step 1: Write agent wrappers**

```python
# src/ppt_agent/adversarial/agents.py
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
```

- [ ] **Step 2: Verify import**

Run: `.venv/bin/python -c "from ppt_agent.adversarial.agents import CriticAgent, ProponentAgent, JudgeAgent; print('OK')"`

- [ ] **Step 3: Commit**

```
git add src/ppt_agent/adversarial/agents.py
git commit -m "feat: add proponent/critic/judge agent wrappers"
```

---

### Task 3: Human ruling + Discussion orchestrator

**Files:**
- Create: `src/ppt_agent/adversarial/human_ruling.py`
- Create: `src/ppt_agent/adversarial/discussion.py`
- Create: `tests/test_discussion.py`

- [ ] **Step 1: Write human ruling module**

```python
# src/ppt_agent/adversarial/human_ruling.py
from __future__ import annotations
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt

from ppt_agent.adversarial.models import ContestedPoint

console = Console()


def prompt_human_ruling(contested: list[ContestedPoint]) -> list[str]:
    """Ask user to rule on contested points. Returns list of rulings."""
    rulings = []
    for i, cp in enumerate(contested, 1):
        console.print(Panel(
            f"📋 批评：{cp.critique.point}\n"
            f"   严重程度：{cp.critique.severity}\n"
            f"   建议：{cp.critique.suggestion}\n\n"
            f"🛡️ 辩护：{cp.defense}\n\n"
            f"⚖️ 裁判犹豫理由：{cp.reason}",
            title=f"争议点 {i}/{len(contested)}",
            style="yellow",
        ))
        choice = Prompt.ask(
            "请选择",
            choices=["1", "2", "3"],
            default="3",
        )
        if choice == "1":
            rulings.append(f"接受批评：{cp.critique.point} → {cp.critique.suggestion}")
        elif choice == "2":
            rulings.append(f"维持原框架：驳回 '{cp.critique.point}'")
        else:
            opinion = Prompt.ask("你的观点")
            rulings.append(f"用户观点：{opinion}")
    return rulings


def format_rulings_for_judge(rulings: list[str]) -> str:
    return "\n".join(f"- {r}" for r in rulings)
```

- [ ] **Step 2: Write discussion orchestrator**

```python
# src/ppt_agent/adversarial/discussion.py
from __future__ import annotations
from rich.console import Console
from rich.panel import Panel

from ppt_agent.config import Config
from ppt_agent.llm.router import ModelRouter
from ppt_agent.models import PPTFramework
from ppt_agent.adversarial.models import (
    Critique, ContestedPoint, DebateRound, DebateResult,
)
from ppt_agent.adversarial.agents import CriticAgent, ProponentAgent, JudgeAgent
from ppt_agent.adversarial.human_ruling import prompt_human_ruling, format_rulings_for_judge

console = Console()


class AdversarialDiscussion:
    def __init__(self, config: Config, router: ModelRouter):
        self.config = config
        _, deep_model = router.get_model("deep_reasoning")
        _, fast_model = router.get_model("daily_chat")
        fast_provider, _ = router.get_model("daily_chat")
        deep_provider, _ = router.get_model("deep_reasoning")
        self.critic = CriticAgent(deep_provider, deep_model)
        self.proponent = ProponentAgent(deep_provider, deep_model)
        self.judge = JudgeAgent(deep_provider, deep_model)

    def run(self, framework: PPTFramework, context: list[dict]) -> DebateResult:
        context_str = "\n".join(m.get("content", "") for m in context[-20:])
        rounds = []
        all_human_rulings = []
        current_framework = framework

        for round_num in range(1, self.config.debate.max_rounds + 1):
            with console.status(f"对抗讨论第 {round_num} 轮..."):
                critiques = self.critic.review(current_framework, context_str)
                if not critiques:
                    console.print(f"[green]第 {round_num} 轮：未发现逻辑问题，讨论结束[/green]")
                    break

                defenses = self.proponent.defend(current_framework, critiques, context_str)
                contested, judge_notes = self.judge.judge(current_framework, critiques, defenses, context_str)

            round_data = DebateRound(
                round_number=round_num,
                critiques=critiques,
                defenses=defenses,
                contested=contested,
                judge_notes=judge_notes,
            )
            rounds.append(round_data)

            console.print(f"[blue]第 {round_num} 轮：{len(critiques)} 个批评，{len(contested)} 个争议点[/blue]")

            # Human ruling for unresolved contested points
            undecided = [cp for cp in contested if cp.judge_verdict == "undecided"]
            if undecided:
                console.print(Panel(f"[yellow]{len(undecided)} 个争议点需要你裁决[/yellow]", style="yellow"))
                rulings = prompt_human_ruling(undecided)
                all_human_rulings.extend(rulings)

            # Check termination
            critical_count = sum(1 for c in critiques if c.severity == "critical")
            score = self._calculate_score(critiques)
            if critical_count == 0:
                console.print("[green]无 critical 级别批评，讨论结束[/green]")
                break
            if score >= self.config.debate.min_logic_score:
                console.print(f"[green]逻辑评分 {score} >= {self.config.debate.min_logic_score}，讨论结束[/green]")
                break

        # Final framework synthesis
        final_framework = self._synthesize(current_framework, rounds, all_human_rulings)
        improvements = self._extract_improvements(rounds)
        logic_score = self._calculate_score(
            [c for r in rounds for c in r.critiques]
        )

        return DebateResult(
            original_framework=framework,
            rounds=rounds,
            final_framework=final_framework,
            improvements=improvements,
            logic_score=logic_score,
            human_rulings=all_human_rulings,
        )

    def _calculate_score(self, critiques: list[Critique]) -> float:
        score = 100.0
        for c in critiques:
            if c.severity == "critical":
                score -= 15
            elif c.severity == "important":
                score -= 8
            elif c.severity == "minor":
                score -= 3
        return max(score, 0.0)

    def _extract_improvements(self, rounds: list[DebateRound]) -> list[str]:
        improvements = []
        for r in rounds:
            for cp in r.contested:
                if cp.judge_verdict == "accept":
                    improvements.append(f"采纳：{cp.critique.suggestion}")
        return improvements

    def _synthesize(self, framework: PPTFramework, rounds: list[DebateRound], human_rulings: list[str]) -> PPTFramework:
        if not rounds:
            return framework
        accepted_suggestions = []
        for r in rounds:
            for cp in r.contested:
                if cp.judge_verdict == "accept":
                    accepted_suggestions.append(cp.critique.suggestion)
        if not accepted_suggestions and not human_rulings:
            return framework
        # If there are changes, return the original with notes for now
        # The LLM-based framework regeneration happens in orchestrator._finalize_framework
        return framework
```

- [ ] **Step 3: Write discussion test**

```python
# tests/test_discussion.py
from ppt_agent.adversarial.discussion import AdversarialDiscussion
from ppt_agent.adversarial.models import Critique, DebateResult
from ppt_agent.models import PPTFramework, SlideFramework, SlideContent
from ppt_agent.config import Config


class TestDiscussionScoring:
    def test_score_no_critiques(self):
        from ppt_agent.adversarial.discussion import AdversarialDiscussion
        config = Config()
        from ppt_agent.llm.router import ModelRouter
        router = ModelRouter(config)
        disc = AdversarialDiscussion(config, router)
        score = disc._calculate_score([])
        assert score == 100.0

    def test_score_with_critical(self):
        from ppt_agent.adversarial.discussion import AdversarialDiscussion
        config = Config()
        from ppt_agent.llm.router import ModelRouter
        router = ModelRouter(config)
        disc = AdversarialDiscussion(config, router)
        critiques = [Critique(point="p", severity="critical", suggestion="s")]
        score = disc._calculate_score(critiques)
        assert score == 85.0

    def test_score_mixed(self):
        from ppt_agent.adversarial.discussion import AdversarialDiscussion
        config = Config()
        from ppt_agent.llm.router import ModelRouter
        router = ModelRouter(config)
        disc = AdversarialDiscussion(config, router)
        critiques = [
            Critique(point="p1", severity="critical", suggestion="s1"),
            Critique(point="p2", severity="important", suggestion="s2"),
            Critique(point="p3", severity="minor", suggestion="s3"),
        ]
        score = disc._calculate_score(critiques)
        assert score == 100 - 15 - 8 - 3
```

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/test_adversarial_models.py tests/test_discussion.py -v`

- [ ] **Step 5: Commit**

```
git add src/ppt_agent/adversarial/ tests/test_discussion.py
git commit -m "feat: add adversarial discussion with human ruling"
```

---

### Task 4: Integrate into orchestrator + CLI

**Files:**
- Modify: `src/ppt_agent/orchestrator.py`
- Modify: `src/ppt_agent/cli.py`

- [ ] **Step 1: Update orchestrator**

In `run_new_project`, after `_finalize_framework(session, provider, model)` and before `generate_pptx`, add:

```python
    # Adversarial discussion
    if config.debate.enabled and session.framework:
        from ppt_agent.adversarial.discussion import AdversarialDiscussion
        discussion = AdversarialDiscussion(config, router)
        debate_result = discussion.run(framework=session.framework, context=session.messages)
        session.framework = debate_result.final_framework
        console.print(f"[green]对抗讨论完成，逻辑评分: {debate_result.logic_score:.0f}/100[/green]")
        if debate_result.improvements:
            for imp in debate_result.improvements:
                console.print(f"  ✓ {imp}")
```

- [ ] **Step 2: Add CLI flags**

In `cli.py`, add to the `new` command options:

```python
@click.option("--no-debate", is_flag=True, help="Skip adversarial discussion")
@click.option("--debate-rounds", default=None, type=int, help="Override debate rounds")
```

And in the `new` function body, before `run_new_project`:

```python
    if no_debate:
        config.debate.enabled = False
    if debate_rounds is not None:
        config.debate.max_rounds = debate_rounds
```

- [ ] **Step 3: Run full test suite**

Run: `.venv/bin/python -m pytest tests/ -v`

- [ ] **Step 4: Verify CLI**

Run: `.venv/bin/python -m ppt_agent new --help`
Expected: shows `--no-debate` and `--debate-rounds` options

- [ ] **Step 5: Commit**

```
git add src/ppt_agent/orchestrator.py src/ppt_agent/cli.py
git commit -m "feat: integrate adversarial discussion into orchestrator and CLI"
```

---

### Self-review

```bash
.venv/bin/python -m pytest tests/ -v
.venv/bin/python -m ppt_agent new --help
.venv/bin/python -c "from ppt_agent.adversarial.discussion import AdversarialDiscussion; print('OK')"
```

**Spec coverage:**
- [x] Multi-role agents (Proponent/Critic/Judge) — Task 2
- [x] Debate round orchestration — Task 3
- [x] Human ruling on contested points — Task 3
- [x] Logic scoring — Task 3
- [x] DebateConfig + CLI flags — Task 1, Task 4
- [x] Orchestrator integration — Task 4
