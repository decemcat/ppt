from __future__ import annotations
from ppt_agent.config import Config
from ppt_agent.models import PPTFramework, SlideFramework, SlideContent
from ppt_agent.session import Session
from ppt_agent.llm.router import ModelRouter
from ppt_agent.generator.slide_generator import generate_pptx

SYSTEM_PROMPT = """你是PPT Agent，一个专业的技术解决方案PPT生成助手。

你的工作流程：
1. 与用户讨论PPT思路，了解背景、受众、核心论点
2. 基于讨论结果，提出清晰的slide框架（标题+每页类型+核心内容）
3. 确认框架后，生成精美的.pptx文件

风格要求：
- 逻辑清晰，抽象层次合理
- 内容精炼，避免堆砌
- 适合企业技术方案汇报场景

以下是关于该主题的研究资料摘要，供参考：\n\n{research_summary}"""


def orchestrator_task(tui):
    """Runs the full PPT generation pipeline in a worker thread."""
    from ppt_agent.tui import PPTTUI

    def run():
        config = _load_config_from_cli()
        topic = tui.topic
        template_path = tui.template_path
        style_name = tui.style_name

        tui.ui_init_tasks([
            "搜索资料", "研究总结", "用户讨论", "确认框架",
            "对抗辩论", "风格加载", "生成PPT", "视觉质检", "保存会话",
        ])
        tui.ui_log(f"开始新项目: {topic}")

        session = Session(topic=topic)
        session.add_message("system", f"Topic: {topic}")

        if not template_path and not config.template_path:
            tui.ui_log("请输入模板 .pptx 文件路径")
            template_path = tui.input_queue.get()
            tui.ui_log(f"模板: {template_path}")
        elif template_path:
            pass
        else:
            template_path = config.template_path
        session.template_path = template_path

        router = ModelRouter(config)
        provider, model = router.get_model("daily_chat")
        tui.ui_context(f"{config.llm.default_provider}:{model}")

        # Research
        tui.ui_task_start("搜索资料")
        from ppt_agent.research.manager import ResearchManager
        research_mgr = ResearchManager(config)
        results = research_mgr.search(topic)
        tui.ui_log(f"搜索: {len(results.get('web',[]))}网页 {len(results.get('papers',[]))}论文 {len(results.get('github',[]))}项目")
        tui.ui_task_done("搜索资料")

        tui.ui_task_start("研究总结")
        summary = research_mgr.summarize(results)
        session.add_message("system", f"Research results:\n{summary}")
        tui.ui_task_done("研究总结")

        # Discussion
        tui.ui_task_start("用户讨论")
        tui.ui_log("请描述你的PPT思路，输入 /done 结束讨论")
        while True:
            user_input = tui.input_queue.get()
            if user_input.strip().lower() == "/done":
                break
            if user_input.strip().lower() == "/framework":
                if session.framework:
                    for i, slide in enumerate(session.framework.framework.slides):
                        tui.ui_log(f"  {i+1}. [{slide.slide_type}] {slide.title}")
                else:
                    tui.ui_log("  框架尚未确定")
                continue
            session.add_message("user", user_input)
            tui.ui_log(f"[bold cyan]You:[/bold cyan] {user_input[:200]}")
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT.replace("{research_summary}", summary)},
                *[{"role": m["role"], "content": m["content"]} for m in session.messages[-10:]],
            ]
            tui.ui_log("[dim]思考中...[/dim]")
            response = provider.chat(messages, model=model)
            session.add_message("assistant", response)
            tui.ui_log(f"{response}")
        tui.ui_task_done("用户讨论")

        # Framework
        tui.ui_task_start("确认框架")
        _finalize_framework(session, provider, model, tui)
        tui.ui_task_done("确认框架")

        # Debate
        if config.debate.enabled and session.framework:
            tui.ui_task_start("对抗辩论")
            from ppt_agent.adversarial.discussion import AdversarialDiscussion
            discussion = AdversarialDiscussion(config, router)
            debate_result = discussion.run(framework=session.framework, context=session.messages)
            session.framework = debate_result.final_framework
            tui.ui_log(f"辩论完成，评分: {debate_result.logic_score:.0f}/100")
            for imp in debate_result.improvements:
                tui.ui_log(f"  ✓ {imp}")
            tui.ui_task_done("对抗辩论")
        else:
            tui.ui_task_done("对抗辩论")

        # Style
        tui.ui_task_start("风格加载")
        style_profile = None
        if style_name:
            from ppt_agent.style.profile import StyleProfile as _SP
            try:
                style_profile = _SP.load(style_name)
                tui.ui_log(f"已加载风格: {style_name}")
            except FileNotFoundError:
                tui.ui_log(f"风格 '{style_name}' 未找到")
        else:
            from ppt_agent.style.profile import StyleProfile as _SP
            try:
                style_profile = _SP.load("default")
            except FileNotFoundError:
                pass
        tui.ui_task_done("风格加载")

        # Generate
        tui.ui_task_start("生成PPT")
        from ppt_agent.generator.image_gen import ImageGenerator
        image_gen = ImageGenerator(config, router)
        output = generate_pptx(
            ppt_framework=session.framework,
            template_path=template_path,
            style_profile=style_profile,
            image_gen=image_gen,
        )
        tui.ui_log(f"PPT已生成: {output}")
        tui.ui_task_done("生成PPT")

        # Visual check
        if config.visual_check.enabled:
            tui.ui_task_start("视觉质检")
            from ppt_agent.quality.checker import VisualQualityChecker
            checker = VisualQualityChecker(config, router)
            check_result = checker.check(output)
            tui.ui_log(check_result.summary)
            if not check_result.passed:
                tui.ui_log(f"⚠ 质检评分 {check_result.total_score:.1f}/10 低于阈值")
            tui.ui_task_done("视觉质检")
        else:
            tui.ui_task_done("视觉质检")

        # Save
        tui.ui_task_start("保存会话")
        session.add_message("system", f"Generated: {output}")
        session.save()
        tui.ui_log("✅ 会话已保存")
        tui.ui_task_done("保存会话")

        tui.ui_log(f"[green]✅ PPT已生成: {output}[/green]")

    return run


def _finalize_framework(session: Session, provider, model: str, tui):
    messages = [
        {"role": "system", "content": "基于对话历史，输出最终的PPT框架。"},
        *[{"role": m["role"], "content": m["content"]} for m in session.messages],
        {"role": "user", "content": "请根据讨论输出最终的PPT框架，包含slides列表。每页有title、slide_type（title/text/arch_diagram/bullets/section_header）、bullets列表和可选的diagram字段。注意：仅在极少情况下，可对个别slide填写image_prompt。最多1-2张。"},
    ]
    tui.ui_log("整理框架中...")
    try:
        framework = provider.chat_structured(messages, PPTFramework, model=model)
        session.framework = framework
        for i, slide in enumerate(framework.framework.slides):
            tui.ui_log(f"  {i+1}. [{slide.slide_type}] {slide.title}")
    except Exception as e:
        tui.ui_log("框架解析出错，使用默认结构")
        session.framework = PPTFramework(
            title=session.topic,
            framework=SlideFramework(slides=[
                SlideContent(title=session.topic, slide_type="title"),
                SlideContent(title="背景", slide_type="text", bullets=["内容待补充"]),
                SlideContent(title="方案总览", slide_type="arch_diagram"),
                SlideContent(title="总结", slide_type="text", bullets=["内容待补充"]),
            ]),
        )


# Module-level config cache set by CLI
_config: Config | None = None


def set_config(config: Config):
    global _config
    _config = config


def _load_config_from_cli() -> Config:
    if _config is None:
        return Config()
    return _config


def run_new_project(
    topic: str,
    config: Config,
    template_path: str | None = None,
    model_override: str | None = None,
    style_name: str | None = None,
):
    """Entry point — starts the Textual TUI in the main thread."""
    import queue
    set_config(config)
    from ppt_agent.tui import PPTTUI
    q = queue.Queue()
    app = PPTTUI(q, topic=topic, template_path=template_path, style_name=style_name)
    app.run()


def run_resume_session(session_path: str, config: Config):
    """Resume a session via the Textual TUI."""
    import queue
    set_config(config)
    from ppt_agent.tui import PPTTUI
    q = queue.Queue()
    app = PPTTUI(q, topic=f"resume:{session_path}", template_path=None, style_name=None)
    app.run()
