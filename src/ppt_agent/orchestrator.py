from __future__ import annotations
from ppt_agent.config import Config
from ppt_agent.models import PPTFramework, SlideFramework, SlideContent
from ppt_agent.session import Session
from ppt_agent.llm.router import ModelRouter
from ppt_agent.generator.slide_generator import generate_pptx

SYSTEM_PROMPT = """你是PPT Agent，一个专业的技术解决方案PPT生成助手。
工作流程: 1.讨论PPT思路 2.提出slide框架 3.生成.pptx文件
风格: 逻辑清晰、内容精炼、适合企业技术方案汇报

参考资料:\n\n{research_summary}"""

_config: Config | None = None


def set_config(c: Config):
    global _config
    _config = c


def orchestrator_task(tui):
    def run():
        c = _config or Config()
        topic = tui.topic
        tpl = tui.template_path or c.template_path
        stl = tui.style_name

        tui.ui_init_tasks(["搜索资料","研究总结","用户讨论","确认框架","对抗辩论","风格加载","生成PPT","视觉质检","保存会话"])
        tui.ui_task_desc(f"项目: {topic}")
        tui.ui_log(f"开始新项目: {topic}")

        session = Session(topic=topic)
        session.add_message("system", f"Topic: {topic}")

        if not tpl:
            tui.ui_task_desc("请输入模板路径")
            val = tui.get_input(timeout=120)
            if val is None or tui._stop_event.is_set():
                return
            tpl = val
        session.template_path = tpl

        router = ModelRouter(c)
        provider, model = router.get_model("daily_chat")
        tui.ui_model(f"{c.llm.default_provider}:{model}")

        tui.ui_task_running("搜索资料")
        from ppt_agent.research.manager import ResearchManager
        if tui._stop_event.is_set():
            return
        mgr = ResearchManager(c)
        results = mgr.search(topic)
        tui.ui_log(f"搜索: {len(results.get('web',[]))}网页 {len(results.get('papers',[]))}论文 {len(results.get('github',[]))}项目")
        tui.ui_task_done("搜索资料")

        tui.ui_task_running("研究总结")
        if tui._stop_event.is_set():
            return
        summary = mgr.summarize(results)
        session.add_message("system", f"Research:\n{summary}")
        tui.ui_task_done("研究总结")
        _est_ctx(tui, summary)

        tui.ui_task_running("用户讨论")
        while True:
            ui = tui.get_input()
            if ui is None or tui._stop_event.is_set():
                return
            if ui.strip().lower() == "/done":
                break
            if ui.strip().lower() == "/framework":
                if session.framework:
                    for i, s in enumerate(session.framework.framework.slides):
                        tui.ui_log(f"  {i+1}. [{s.slide_type}] {s.title}")
                else:
                    tui.ui_log("  框架尚未确定")
                continue
            session.add_message("user", ui)
            tui.ui_log(f"[bold cyan]You:[/bold cyan] {ui[:200]}")
            msgs = [
                {"role":"system","content": SYSTEM_PROMPT.replace("{research_summary}", summary)},
                *[{"role":m["role"],"content":m["content"]} for m in session.messages[-10:]],
            ]
            _est_ctx(tui, summary)
            tui.ui_task_desc("思考中...")
            if tui._stop_event.is_set():
                return
            resp = provider.chat(msgs, model=model)
            if tui._stop_event.is_set():
                return
            session.add_message("assistant", resp)
            tui.ui_log(f"{resp}")
            tui.ui_task_desc("等待输入")
        tui.ui_task_done("用户讨论")

        tui.ui_task_running("确认框架")
        if tui._stop_event.is_set():
            return
        tui.ui_task_desc("整理框架中...")
        _finalize(session, provider, model, tui)
        tui.ui_task_done("确认框架")

        if c.debate.enabled and session.framework:
            tui.ui_task_running("对抗辩论")
            if tui._stop_event.is_set():
                return
            from ppt_agent.adversarial.discussion import AdversarialDiscussion
            disc = AdversarialDiscussion(c, router)
            dr = disc.run(framework=session.framework, context=session.messages)
            if tui._stop_event.is_set():
                return
            session.framework = dr.final_framework
            tui.ui_log(f"辩论评分: {dr.logic_score:.0f}/100")
            for imp in dr.improvements:
                tui.ui_log(f"  ✓ {imp}")
            tui.ui_task_done("对抗辩论")
        else:
            tui.ui_task_done("对抗辩论")

        tui.ui_task_running("风格加载")
        sp = None
        if stl:
            from ppt_agent.style.profile import StyleProfile as _SP
            try:
                sp = _SP.load(stl)
            except FileNotFoundError:
                pass
        else:
            from ppt_agent.style.profile import StyleProfile as _SP
            try:
                sp = _SP.load("default")
            except FileNotFoundError:
                pass
        tui.ui_task_done("风格加载")

        tui.ui_task_running("生成PPT")
        if tui._stop_event.is_set():
            return
        tui.ui_task_desc("生成中...")
        from ppt_agent.generator.image_gen import ImageGenerator
        ig = ImageGenerator(c, router)
        output = generate_pptx(session.framework, tpl, style_profile=sp, image_gen=ig)
        tui.ui_log(f"PPT: {output}")
        tui.ui_task_done("生成PPT")

        if c.visual_check.enabled:
            tui.ui_task_running("视觉质检")
            if tui._stop_event.is_set():
                return
            from ppt_agent.quality.checker import VisualQualityChecker
            vc = VisualQualityChecker(c, router)
            cr = vc.check(output)
            tui.ui_log(cr.summary)
            tui.ui_task_done("视觉质检")
        else:
            tui.ui_task_done("视觉质检")

        tui.ui_task_running("保存会话")
        session.add_message("system", f"Generated: {output}")
        session.save()
        tui.ui_task_done("保存会话")
        tui.ui_task_desc("完成")
        tui.ui_log(f"[green]✅ PPT已生成: {output}[/green]")
    return run


def _est_ctx(tui, text: str):
    tok = len(text) // 4
    tui.ui_tokens(tok)
    tui.ui_context_pct(min(tok * 100 // 128000, 100))


def _finalize(session, provider, model, tui):
    msgs = [
        {"role":"system","content":"输出最终的PPT框架。"},
        *[{"role":m["role"],"content":m["content"]} for m in session.messages],
        {"role":"user","content":"输出PPT框架，每页有title/slide_type/bullets/diagram。仅极少情况填image_prompt，最多1-2张。"},
    ]
    try:
        fw = provider.chat_structured(msgs, PPTFramework, model=model)
        session.framework = fw
        for i, s in enumerate(fw.framework.slides):
            tui.ui_log(f"  {i+1}. [{s.slide_type}] {s.title}")
    except Exception:
        tui.ui_log("框架解析出错，使用默认结构")
        session.framework = PPTFramework(
            title=session.topic,
            framework=SlideFramework(slides=[
                SlideContent(title=session.topic, slide_type="title"),
                SlideContent(title="背景", slide_type="text", bullets=["待补充"]),
                SlideContent(title="方案", slide_type="arch_diagram"),
                SlideContent(title="总结", slide_type="text", bullets=["待补充"]),
            ]),
        )


def run_new_project(topic, config, template_path=None, model_override=None, style_name=None):
    import queue
    set_config(config)
    from ppt_agent.tui import PPTTUI
    app = PPTTUI(queue.Queue(), topic=topic, template_path=template_path, style_name=style_name)
    app.run()


def run_resume_session(session_path, config):
    import queue
    set_config(config)
    from ppt_agent.tui import PPTTUI
    app = PPTTUI(queue.Queue(), topic=f"resume:{session_path}")
    app.run()
