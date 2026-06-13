from __future__ import annotations
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from ppt_agent.config import Config
from ppt_agent.models import PPTFramework, SlideFramework, SlideContent
from ppt_agent.session import Session
from ppt_agent.llm.router import ModelRouter
from ppt_agent.generator.slide_generator import generate_pptx

console = Console()

SYSTEM_PROMPT = """你是PPT Agent，一个专业的技术解决方案PPT生成助手。

你的工作流程：
1. 与用户讨论PPT思路，了解背景、受众、核心论点
2. 基于讨论结果，提出清晰的slide框架（标题+每页类型+核心内容）
3. 确认框架后，生成精美的.pptx文件

风格要求：
- 逻辑清晰，抽象层次合理
- 内容精炼，避免堆砌
- 适合企业技术方案汇报场景

当前阶段：讨论阶段。请与用户深入交流，不要急于定框架。

以下是关于该主题的研究资料摘要，供参考：\n\n{research_summary}"""


def run_new_project(
    topic: str,
    config: Config,
    template_path: str | None = None,
    model_override: str | None = None,
):
    """Entry point for `ppt-agent new`."""
    session = Session(topic=topic)
    session.add_message("system", f"Topic: {topic}")
    console.print(Panel(f"[bold]开始新项目:[/bold] {topic}", style="blue"))
    if not template_path and not config.template_path:
        template_path = Prompt.ask("请输入模板 .pptx 文件路径")
    elif template_path:
        pass
    else:
        template_path = config.template_path
    session.template_path = template_path
    router = ModelRouter(config)
    provider, model = router.get_model("daily_chat")
    # Research phase
    console.print(Panel("[bold]正在搜索相关知识...[/bold]", style="blue"))
    from ppt_agent.research.manager import ResearchManager
    research_mgr = ResearchManager(config)
    results = research_mgr.search(topic)
    summary = research_mgr.summarize(results)
    session.add_message("system", f"Research results:\n{summary}")
    total = len(results.get("web", [])) + len(results.get("papers", [])) + len(results.get("github", []))
    console.print(f"[green]✓ 找到 {len(results.get('web', []))} 篇网页、{len(results.get('papers', []))} 篇论文、{len(results.get('github', []))} 个相关项目[/green]")
    console.print(Panel("请描述你的PPT思路，我会与你讨论并帮助完善框架。输入 /done 结束讨论进入生成阶段。", style="green"))
    while True:
        user_input = Prompt.ask("[bold you]")
        if user_input.strip().lower() == "/done":
            break
        if user_input.strip().lower() == "/framework":
            _show_current_framework(session)
            continue
        session.add_message("user", user_input)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT.replace("{research_summary}", summary)},
            *[{"role": m["role"], "content": m["content"]} for m in session.messages[-10:]],
        ]
        with console.status("思考中..."):
            response = provider.chat(messages, model=model)
        session.add_message("assistant", response)
        console.print(Panel(response, style="yellow"))
    console.print(Panel("正在确认最终框架...", style="blue"))
    _finalize_framework(session, provider, model)
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
    console.print(Panel("正在生成PPT...", style="blue"))
    output = generate_pptx(
        ppt_framework=session.framework,
        template_path=template_path,
    )
    session.add_message("system", f"Generated: {output}")
    session.save()
    console.print(f"[green]✅ PPT已生成: {output}[/green]")


def run_resume_session(session_path: str, config: Config):
    """Resume a previous session."""
    session = Session.load(session_path)
    console.print(Panel(f"[bold]恢复会话:[/bold] {session.topic}", style="blue"))
    router = ModelRouter(config)
    provider, model = router.get_model("daily_chat")
    for msg in session.messages[-5:]:
        role = "you" if msg["role"] == "user" else "assistant"
        console.print(f"[bold {role}:] {msg['content']}")
    console.print(Panel("继续讨论。输入 /done 结束讨论并重新生成。", style="green"))
    summary = session.messages[0].get("content", "") if session.messages else ""
    while True:
        user_input = Prompt.ask("[bold you]")
        if user_input.strip().lower() == "/done":
            break
        session.add_message("user", user_input)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT.replace("{research_summary}", summary)},
            *[{"role": m["role"], "content": m["content"]} for m in session.messages[-10:]],
        ]
        with console.status("思考中..."):
            response = provider.chat(messages, model=model)
        session.add_message("assistant", response)
        console.print(Panel(response, style="yellow"))
    _finalize_framework(session, provider, model)
    template_path = session.template_path or config.template_path
    output = generate_pptx(
        ppt_framework=session.framework,
        template_path=template_path,
    )
    session.save()
    console.print(f"[green]✅ PPT已重新生成: {output}[/green]")


def _show_current_framework(session: Session):
    if session.framework:
        for i, slide in enumerate(session.framework.framework.slides):
            console.print(f"  {i+1}. [{slide.slide_type}] {slide.title}")
    else:
        console.print("  框架尚未确定")


def _finalize_framework(session: Session, provider, model: str):
    """Use LLM to produce final structured framework from conversation history."""
    messages = [
        {"role": "system", "content": "基于对话历史，输出最终的PPT框架。"},
        *[{"role": m["role"], "content": m["content"]} for m in session.messages],
        {"role": "user", "content": "请根据讨论输出最终的PPT框架，包含slides列表。每页有title、slide_type（title/text/arch_diagram/bullets/section_header）、bullets列表和可选的diagram字段。"},
    ]
    with console.status("正在整理框架..."):
        try:
            framework = provider.chat_structured(messages, PPTFramework, model=model)
            session.framework = framework
            console.print("[green]框架已确认:[/green]")
            _show_current_framework(session)
        except Exception as e:
            console.print(f"[yellow]框架解析出错，使用默认结构: {e}[/yellow]")
            session.framework = PPTFramework(
                title=session.topic,
                framework=SlideFramework(slides=[
                    SlideContent(title=session.topic, slide_type="title"),
                    SlideContent(title="背景", slide_type="text", bullets=["内容待补充"]),
                    SlideContent(title="方案总览", slide_type="arch_diagram"),
                    SlideContent(title="总结", slide_type="text", bullets=["内容待补充"]),
                ]),
            )
