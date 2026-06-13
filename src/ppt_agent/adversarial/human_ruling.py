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
