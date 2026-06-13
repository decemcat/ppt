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


def _confirm(tui, prompt_text: str) -> bool:
    tui.ui_log(f"[yellow]?[/yellow] {prompt_text} [dim](Enter=yes, n=no)[/dim]")
    val = tui.get_input(timeout=120)
    if val is None or tui._stop_event.is_set():
        return False
    return val.strip().lower() not in ("n", "no")


def orchestrator_task(tui):
    def run():
        c = _config or Config()
        topic = tui.topic
        tpl = tui.template_path or c.template_path
        stl = tui.style_name

        tui.ui_init_tasks(["Research","Summarize","Discuss","Framework","Debate","Style","Generate","Visual Check","Save"])
        tui.ui_task_desc(f"Project: {topic}")
        tui.ui_log(f"[bold]● {topic}[/bold]")
        tui.ui_log("[dim]─" * 40 + "[/dim]")

        session = Session(topic=topic)
        session.add_message("system", f"Topic: {topic}")

        if not tpl:
            tui.ui_task_desc("Enter template path")
            val = tui.get_input(timeout=120)
            if val is None or tui._stop_event.is_set():
                return
            tpl = val
        session.template_path = tpl

        router = ModelRouter(c)
        provider, model = router.get_model("daily_chat")
        tui.ui_model(f"{c.llm.default_provider}:{model}")
        tui.ui_log(f"[dim]Model: {c.llm.default_provider}:{model}[/dim]")

        tui.ui_task_running("Research")
        from ppt_agent.research.manager import ResearchManager
        from ppt_agent.research.web_searcher import WebSearcher
        from ppt_agent.research.paper_searcher import PaperSearcher
        from ppt_agent.research.github_analyzer import GitHubAnalyzer
        if tui._stop_event.is_set():
            return
        mgr = ResearchManager(c)

        tui.ui_log("[bold]▸ Web Search[/bold]")
        tui.ui_subagent_add("web", "searching")
        tui.ui_busy("DuckDuckGo web search")
        tui.ui_log(f"  query: [dim]{topic}[/dim]")
        tui.ui_log(f"  engine: DuckDuckGo")
        web_searcher = WebSearcher(proxy=c.proxy)
        web_results = web_searcher.search(topic, num_results=5)
        tui.ui_busy("")
        tui.ui_subagent_done("web")
        if web_results:
            tui.ui_log(f"  [green]✓[/green] [bold]{len(web_results)}[/bold] results")
            for i, r in enumerate(web_results):
                tui.ui_log(f"    {i+1}. [bold]{r.title}[/bold]")
                tui.ui_log(f"       [dim]{r.url}[/dim]")
        else:
            tui.ui_log(f"  [dim]no results[/dim]")

        tui.ui_log("[bold]▸ Paper Search[/bold]")
        tui.ui_subagent_add("papers", "searching")
        tui.ui_busy("Searching arXiv & Semantic Scholar")
        tui.ui_log(f"  sources: arXiv, Semantic Scholar")
        paper_searcher = PaperSearcher(proxy=c.proxy)
        paper_results = paper_searcher.search(topic, max_results=5)
        tui.ui_busy("")
        tui.ui_subagent_done("papers")
        if paper_results:
            tui.ui_log(f"  [green]✓[/green] [bold]{len(paper_results)}[/bold] papers")
            for i, p in enumerate(paper_results):
                arxiv_id = getattr(p, "arxiv_id", "")[:10] or "—"
                citations = getattr(p, "citations", 0) or 0
                authors = ", ".join(getattr(p, "authors", [])[:3] or [])
                tui.ui_log(f"    {i+1}. [bold]{p.title}[/bold]")
                tui.ui_log(f"       arXiv: {arxiv_id}  citations: {citations}")
                if authors:
                    tui.ui_log(f"       by {authors}")
        else:
            tui.ui_log(f"  [dim]no results[/dim]")

        tui.ui_log("[bold]▸ GitHub Search[/bold]")
        tui.ui_subagent_add("github", "searching")
        tui.ui_busy("Searching GitHub repositories")
        tui.ui_log(f"  query: [dim]{topic} sort:stars[/dim]")
        gh_analyzer = GitHubAnalyzer()
        gh_results = gh_analyzer.search(topic, max_results=5)
        tui.ui_busy("")
        tui.ui_subagent_done("github")
        if gh_results:
            tui.ui_log(f"  [green]✓[/green] [bold]{len(gh_results)}[/bold] repos")
            for i, r in enumerate(gh_results):
                tui.ui_log(f"    {i+1}. [bold]{r.repo}[/bold] ★{r.stars}")
                if r.description:
                    tui.ui_log(f"       [dim]{r.description[:120]}[/dim]")
        else:
            tui.ui_log(f"  [dim]no results[/dim]")

        results = {"web": web_results, "papers": paper_results, "github": gh_results}

        tui.ui_busy("Indexing to ChromaDB & knowledge graph")
        try:
            for source_type, items in results.items():
                docs = []
                for item in items:
                    text = getattr(item, "content", "") or getattr(item, "snippet", "") or getattr(item, "description", "")
                    url = getattr(item, "url", "")
                    title = getattr(item, "title", "") or getattr(item, "repo", "")
                    docs.append({
                        "id": f"{source_type}_{hash(url) % 100000:05d}",
                        "text": text,
                        "metadata": {"source": source_type, "url": url, "title": title},
                    })
                if docs:
                    mgr.indexer.add_documents(docs, collection="knowledge")
            tui.ui_log(f"  [green]✓[/green] Indexed to ChromaDB")
        except Exception:
            pass
        try:
            for items in results.values():
                search_results = [item for item in items if hasattr(item, "source")]
                mgr.graph.auto_index(search_results)
            mgr.graph.save(c.knowledge.resolved_graph_path)
            tui.ui_log(f"  [green]✓[/green] Knowledge graph updated")
        except Exception:
            pass
        tui.ui_busy("")

        tui.ui_task_running("Summarize")
        if tui._stop_event.is_set():
            return
        tui.ui_subagent_add("summarize", "summarizing research")
        total_items = sum(len(v) for v in results.values())
        tui.ui_log(f"  sources: [bold]{total_items}[/bold] total ({len(web_results)} web + {len(paper_results)} papers + {len(gh_results)} repos)")
        tui.ui_busy(f"Summarizing {total_items} sources")
        summary = mgr.summarize(results)
        tui.ui_busy("")
        tui.ui_subagent_done("summarize")
        tui.ui_subagent_done("summarize")
        session.add_message("system", f"Research:\n{summary}")
        tui.ui_task_done("Summarize")
        tui.ui_log(f"  [green]✓[/green] Research summary ready ({len(summary)} chars)")
        _est_ctx(tui, summary)

        tui.ui_log("[dim]─" * 40 + "[/dim]")
        tui.ui_log("[bold]▸ Discussion[/bold]")
        tui.ui_task_running("Discuss")
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
                    tui.ui_log("  framework not ready")
                continue
            session.add_message("user", ui)
            tui.ui_log(f"[bold cyan]You:[/bold cyan] {ui[:200]}")
            msgs = [
                {"role":"system","content": SYSTEM_PROMPT.replace("{research_summary}", summary)},
                *[{"role":m["role"],"content":m["content"]} for m in session.messages[-10:]],
            ]
            _est_ctx(tui, summary)
            tui.ui_task_desc("Thinking...")
            if tui._stop_event.is_set():
                return
            tui.ui_busy(f"Agent: {ui[:60]}...")
            resp = provider.chat(msgs, model=model)
            tui.ui_busy("")
            if tui._stop_event.is_set():
                return
            session.add_message("assistant", resp)
            tui.ui_log(f"{resp}")
            tui.ui_task_desc("Awaiting input")
        tui.ui_task_done("Discuss")

        tui.ui_log("[dim]─" * 40 + "[/dim]")
        tui.ui_log("[bold]▸ Framework[/bold]")
        tui.ui_task_running("Framework")
        if tui._stop_event.is_set():
            return
        tui.ui_task_desc("Building framework...")
        tui.ui_busy("Building slide framework")
        _finalize(session, provider, model, tui)
        tui.ui_busy("")
        tui.ui_task_done("Framework")

        if c.debate.enabled and session.framework:
            if not _confirm(tui, f"Start adversarial debate? ({len(session.framework.framework.slides)} slides)"):
                tui.ui_log(f"  [dim]debate skipped[/dim]")
                tui.ui_task_done("Debate")
            else:
                tui.ui_log("[bold]▸ Debate[/bold]")
                tui.ui_task_running("Debate")
                if tui._stop_event.is_set():
                    return
                from ppt_agent.adversarial.discussion import AdversarialDiscussion
                disc = AdversarialDiscussion(c, router)
                tui.ui_subagent_add("proponent", "arguing")
                tui.ui_subagent_add("critic", "critiquing")
                tui.ui_subagent_add("judge", "evaluating")
                tui.ui_busy("Running adversarial debate")
                dr = disc.run(framework=session.framework, context=session.messages)
                tui.ui_busy("")
                tui.ui_subagent_done("proponent")
                tui.ui_subagent_done("critic")
                tui.ui_subagent_done("judge")
                if tui._stop_event.is_set():
                    return
                session.framework = dr.final_framework
                tui.ui_log(f"  [green]✓[/green] Logic score: [bold]{dr.logic_score:.0f}/100[/bold]")
                for imp in dr.improvements:
                    tui.ui_log(f"  [green]+[/green] {imp}")
                tui.ui_task_done("Debate")
        else:
            tui.ui_task_done("Debate")

        tui.ui_task_running("Style")
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
        if sp:
            tui.ui_log(f"  [green]✓[/green] Style loaded: [bold]{sp.name}[/bold]")
        tui.ui_task_done("Style")

        if not _confirm(tui, f"Generate PPTX?"):
            tui.ui_log(f"  [dim]generation aborted[/dim]")
            tui.ui_task_desc("Aborted")
            return

        tui.ui_log("[dim]─" * 40 + "[/dim]")
        tui.ui_log("[bold]▸ Generate[/bold]")
        tui.ui_task_running("Generate")
        if tui._stop_event.is_set():
            return
        tui.ui_task_desc("Generating PPTX...")
        from ppt_agent.generator.image_gen import ImageGenerator
        ig = ImageGenerator(c, router)
        tui.ui_busy("Generating PPTX file")
        def on_slide_progress(idx, total, slide):
            tui.ui_log(f"  [{idx}/{total}] [{slide.slide_type}] {slide.title}")
            tui.ui_busy(f"Slide {idx}/{total}")
        output = generate_pptx(session.framework, tpl, style_profile=sp, image_gen=ig, on_progress=on_slide_progress)
        tui.ui_busy("")
        tui.ui_log(f"  [green]✓[/green] [bold]{output}[/bold]")
        tui.ui_task_done("Generate")

        if c.visual_check.enabled:
            tui.ui_task_running("Visual Check")
            if tui._stop_event.is_set():
                return
            from ppt_agent.quality.checker import VisualQualityChecker
            vc = VisualQualityChecker(c, router)
            tui.ui_subagent_add("vision", "evaluating slides")
            tui.ui_busy("Running visual quality check")
            cr = vc.check(output)
            tui.ui_busy("")
            tui.ui_subagent_done("vision")
            tui.ui_log(f"  [green]✓[/green] {cr.summary}")
            tui.ui_task_done("Visual Check")
        else:
            tui.ui_task_done("Visual Check")

        tui.ui_task_running("Save")
        session.add_message("system", f"Generated: {output}")
        session.save()
        tui.ui_task_done("Save")
        tui.ui_task_desc("Done")
        tui.ui_log("[dim]─" * 40 + "[/dim]")
        tui.ui_log(f"[green bold]● Done: {output}[/green bold]")
    return run


def _est_ctx(tui, text: str):
    tok = len(text) // 4
    tui.ui_tokens(tok)
    tui.ui_context_pct(min(tok * 100 // 128000, 100))


def _finalize(session, provider, model, tui):
    msgs = [
        {"role":"system","content":"Output the final PPT framework."},
        *[{"role":m["role"],"content":m["content"]} for m in session.messages],
        {"role":"user","content":"Output PPT framework with title/slide_type/bullets/diagram per slide. Only use image_prompt sparingly, 1-2 max."},
    ]
    try:
        fw = provider.chat_structured(msgs, PPTFramework, model=model)
        session.framework = fw
        for i, s in enumerate(fw.framework.slides):
            tui.ui_log(f"  {i+1}. [{s.slide_type}] {s.title}")
    except Exception:
        tui.ui_log("Framework parse error, using defaults")
        session.framework = PPTFramework(
            title=session.topic,
            framework=SlideFramework(slides=[
                SlideContent(title=session.topic, slide_type="title"),
                SlideContent(title="Background", slide_type="text", bullets=["TBD"]),
                SlideContent(title="Solution", slide_type="arch_diagram"),
                SlideContent(title="Summary", slide_type="text", bullets=["TBD"]),
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
