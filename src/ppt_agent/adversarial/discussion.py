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
