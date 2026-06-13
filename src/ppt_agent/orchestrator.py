from __future__ import annotations
from ppt_agent.config import Config
from ppt_agent.models import PPTFramework, SlideFramework, SlideContent
from ppt_agent.session import Session
from ppt_agent.llm.router import ModelRouter
from ppt_agent.generator.slide_generator import generate_pptx

SYSTEM_PROMPT = """You are PPT Agent, a professional technical presentation assistant.

Workflow:
1. Understand the problem domain and user's knowledge needs
2. Research deeply to gather insights, facts, and expert perspectives
3. Summarize key findings
4. Discuss how to structure the presentation based on insights
5. Build a slide framework
6. Generate .pptx file

Be concise, logical, and focused on substance over format."""

REQUIREMENTS_PROMPT = """You are a business/technical consultant doing discovery. Your goal is to deeply understand the user's domain, problem, and what they need to communicate — NOT to plan slides yet.

Ask probing questions to clarify:
1. What problem or topic do they want to communicate about? Why now?
2. Who are they trying to convince or inform? What would change their mind?
3. What do they already know vs what needs external research?
4. What's their unique angle or perspective on this topic?
5. What are the stakes — what happens if communication succeeds or fails?

DO NOT ask about slide count, format, templates, or presentation style. Focus entirely on understanding the subject matter and communication goals. When you have a clear picture of the domain and needs, say "/ready".

Current context:\n\n{history}"""

RESEARCH_PLAN_PROMPT = """Based on the domain and communication needs discussed above, propose a research plan to gather insights.

Output a concise plan with:
1. Key areas to investigate — what knowledge gaps to fill (3-5 bullet points)
2. Search queries for web/papers/GitHub (3-5 specific queries targeting the domain)
3. What kind of insights we're looking for (data, case studies, expert opinions, trends, trade-offs)

Focus on learning. The user will confirm before research begins.

Requirements:\n{requirements}"""

PPT_DISCUSSION_PROMPT = """You have deep research insights about the topic. Now help the user plan how to structure their presentation.

Based on the research below, discuss:
1. What are the most compelling insights that should go into the presentation?
2. What narrative structure would work best given the audience and goals?
3. What key messages should each section convey?
4. What diagrams or visuals would help communicate complex ideas?

When the user is satisfied with the direction, type /done.

Research:\n{research_summary}"""

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


def _chat_loop(tui, session, provider, model, system_prompt, end_cmd="/done", label="Discuss"):
    while True:
        ui = tui.get_input()
        if ui is None or tui._stop_event.is_set():
            return None
        if ui.strip().lower() == end_cmd:
            break
        if ui.strip().lower() == "/framework":
            if session.framework:
                for i, s in enumerate(session.framework.framework.slides):
                    tui.ui_log(f"  {i+1}. [{s.slide_type}] {s.title}")
            else:
                tui.ui_log("  [dim]framework not ready[/dim]")
            continue
        session.add_message("user", ui)
        tui.ui_log(f"[bold cyan]You:[/bold cyan] {ui[:200]}")
        msgs = [
            {"role": "system", "content": system_prompt},
            *[{"role": m["role"], "content": m["content"]} for m in session.messages[-12:]],
        ]
        tui.ui_task_desc("Thinking...")
        if tui._stop_event.is_set():
            return None
        tui.ui_busy(f"{label}...")
        resp = provider.chat(msgs, model=model)
        tui.ui_busy("")
        if tui._stop_event.is_set():
            return None
        session.add_message("assistant", resp)
        tui.ui_log(f"{resp}")
        tui.ui_task_desc("Awaiting input")
    return session


def _est_ctx(tui, text: str):
    tok = len(text) // 4
    tui.ui_tokens(tok)
    tui.ui_context_pct(min(tok * 100 // 128000, 100))


def _finalize(session, provider, model, tui):
    msgs = [
        {"role": "system", "content": "Output the final PPT framework."},
        *[{"role": m["role"], "content": m["content"]} for m in session.messages],
        {"role": "user", "content": "Output PPT framework with title/slide_type/bullets/diagram per slide. Only use image_prompt sparingly, 1-2 max."},
    ]
    try:
        fw = provider.chat_structured(msgs, PPTFramework, model=model)
        session.framework = fw
        for i, s in enumerate(fw.framework.slides):
            tui.ui_log(f"  {i+1}. [{s.slide_type}] {s.title}")
    except Exception:
        tui.ui_log("  [yellow]![/yellow] Framework parse error, using defaults")
        session.framework = PPTFramework(
            title=session.topic,
            framework=SlideFramework(slides=[
                SlideContent(title=session.topic, slide_type="title"),
                SlideContent(title="Background", slide_type="text", bullets=["TBD"]),
                SlideContent(title="Solution", slide_type="arch_diagram"),
                SlideContent(title="Summary", slide_type="text", bullets=["TBD"]),
            ]),
        )


def _load_style(stl):
    from ppt_agent.style.profile import StyleProfile as _SP
    if stl:
        try:
            return _SP.load(stl)
        except FileNotFoundError:
            pass
    else:
        try:
            return _SP.load("default")
        except FileNotFoundError:
            pass
    return None


def orchestrator_task(tui):
    def run():
        c = _config or Config()

        tui.ui_init_tasks(["Requirements", "Research Plan", "Research", "Summarize", "Discuss", "Framework", "Debate", "Style", "Generate", "Visual Check", "Save"])
        tui.ui_task_desc("Ready")
        tui.ui_log("[bold]● PPT Agent[/bold]")
        tui.ui_log("[dim]Describe your presentation needs, and I'll help you build it.[/dim]")
        tui.ui_log("")

        session = Session(topic="New Presentation")

        router = ModelRouter(c)
        provider, model = router.get_model("daily_chat")
        tui.ui_model(f"{c.llm.default_provider}:{model}")

        # ── Phase 1: Requirements Gathering ──
        tui.ui_log("[bold]▸ Requirements[/bold]")
        tui.ui_log("[dim]Tell me about the problem or topic you want to communicate. What's the context?[/dim]")
        tui.ui_log("[dim]I'll ask questions to understand your domain before we do any research.[/dim]")
        tui.ui_task_running("Requirements")
        tui.ui_task_desc("Understanding your domain")

        req_msgs = [
            {"role": "system", "content": REQUIREMENTS_PROMPT.replace("{history}", "")},
        ]
        while True:
            ui = tui.get_input()
            if ui is None or tui._stop_event.is_set():
                return
            if ui.strip().lower() == "/done":
                break
            if not ui.strip():
                continue
            session.add_message("user", ui)
            tui.ui_log(f"[bold cyan]You:[/bold cyan] {ui[:200]}")
            req_msgs.append({"role": "user", "content": ui})
            hist = "\n".join(m["content"][:300] for m in req_msgs[-6:])
            tui.ui_task_desc("Clarifying domain")
            tui.ui_busy("Understanding your domain")
            resp = provider.chat(
                [{"role": "system", "content": REQUIREMENTS_PROMPT.replace("{history}", hist)}] + req_msgs[-6:],
                model=model,
            )
            tui.ui_busy("")
            if tui._stop_event.is_set():
                return
            req_msgs.append({"role": "assistant", "content": resp})
            session.add_message("assistant", resp)
            tui.ui_log(f"{resp}")
            tui.ui_task_desc("Continue or /done")
            if "/ready" in resp.lower():
                tui.ui_log("[dim](Agent suggests moving on. Type /done or continue.)[/dim]")

        tui.ui_task_done("Requirements")
        requirements_summary = "\n".join(m["content"] for m in req_msgs if m["role"] in ("user", "assistant"))
        tui.ui_log("[dim]─" * 40 + "[/dim]")

        # ── Phase 2: Research Plan ──
        tui.ui_log("[bold]▸ Research Plan[/bold]")
        tui.ui_log("[dim]Based on our discussion, here's what we should investigate:[/dim]")
        tui.ui_task_running("Research Plan")
        tui.ui_task_desc("Planning research")
        tui.ui_busy("Building research plan")

        plan_msg = [
            {"role": "system", "content": RESEARCH_PLAN_PROMPT.replace("{requirements}", requirements_summary)},
        ]
        plan_resp = provider.chat(plan_msg, model=model)
        tui.ui_busy("")
        if tui._stop_event.is_set():
            return
        tui.ui_log(f"{plan_resp}")
        tui.ui_log("")

        if not _confirm(tui, "Execute this research plan?"):
            tui.ui_log("  [dim]Plan rejected. You can refine the requirements:[/dim]")
            tui.ui_log("  [dim]Type your adjustments or /done to confirm.[/dim]")
            while True:
                ui = tui.get_input()
                if ui is None or tui._stop_event.is_set():
                    return
                if ui.strip().lower() == "/done":
                    break
                feedback = f"Refine the research plan based on this feedback: {ui}"
                plan_msg.append({"role": "user", "content": feedback})
                tui.ui_busy("Refining research plan")
                plan_resp = provider.chat(plan_msg, model=model)
                tui.ui_busy("")
                tui.ui_log(f"{plan_resp}")
        tui.ui_task_done("Research Plan")
        tui.ui_log("  [green]✓[/green] Research plan confirmed")

        # Extract search queries from plan
        session.add_message("system", f"Research plan:\n{plan_resp}")
        tui.ui_log("[dim]─" * 40 + "[/dim]")

        # ── Phase 3: Research ──
        tui.ui_task_running("Research")
        from ppt_agent.research.manager import ResearchManager
        from ppt_agent.research.web_searcher import WebSearcher
        from ppt_agent.research.paper_searcher import PaperSearcher
        from ppt_agent.research.github_analyzer import GitHubAnalyzer
        if tui._stop_event.is_set():
            return
        mgr = ResearchManager(c)

        # Determine topic from requirements
        topic = session.topic or "presentation"
        if session.messages:
            for m in reversed(session.messages):
                if m["role"] == "user" and len(m["content"]) > 10:
                    topic = m["content"][:80]
                    break
        session.topic = topic

        # Web
        tui.ui_log("[bold]▸ Web Search[/bold]")
        tui.ui_subagent_add("web", "searching")
        tui.ui_busy("DuckDuckGo + Google + Bing")
        tui.ui_log(f"  query: [dim]{topic}[/dim]")
        tui.ui_log(f"  engines: DuckDuckGo, Google, Bing")
        web_searcher = WebSearcher(proxy=c.proxy)
        t0 = __import__("time").time()
        web_results = web_searcher.search(topic, num_results=5)
        elapsed = __import__("time").time() - t0
        tui.ui_busy("")
        tui.ui_subagent_done("web")
        if web_results:
            tui.ui_log(f"  [green]✓[/green] [bold]{len(web_results)}[/bold] results ({elapsed:.1f}s)")
            for i, r in enumerate(web_results):
                tui.ui_log(f"    {i+1}. [bold]{r.title}[/bold]")
                tui.ui_log(f"       [dim]{r.url}[/dim]")
        else:
            tui.ui_log(f"  [dim]no results[/dim]")

        # Papers
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

        # GitHub
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

        # Index
        tui.ui_busy("Indexing to knowledge base")
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
            mgr.graph.auto_index([item for items in results.values() for item in items if hasattr(item, "source")])
            mgr.graph.save(c.knowledge.resolved_graph_path)
        except Exception:
            pass
        tui.ui_busy("")
        tui.ui_task_done("Research")
        tui.ui_log(f"  [green]✓[/green] Search complete: {len(web_results)} web + {len(paper_results)} papers + {len(gh_results)} repos")

        # ── Phase 4: Summarize ──
        tui.ui_task_running("Summarize")
        if tui._stop_event.is_set():
            return
        tui.ui_subagent_add("summarize", "summarizing research")
        total_items = sum(len(v) for v in results.values())
        tui.ui_busy(f"Summarizing {total_items} sources")
        summary = mgr.summarize(results)
        tui.ui_busy("")
        tui.ui_subagent_done("summarize")
        session.add_message("system", f"Research:\n{summary}")
        tui.ui_task_done("Summarize")
        tui.ui_log(f"  [green]✓[/green] Research summary ready ({len(summary)} chars)")
        _est_ctx(tui, summary)

        # ── Phase 5: Discussion ──
        tui.ui_log("[dim]─" * 40 + "[/dim]")
        tui.ui_log("[bold]▸ PPT Strategy[/bold]")
        tui.ui_log("[dim]Now that we have research insights, let's plan the presentation structure.[/dim]")
        tui.ui_log("[dim]Discuss narrative, key messages, and flow. /done when ready for framework.[/dim]")
        tui.ui_task_running("Discuss")
        result = _chat_loop(tui, session, provider, model,
                            PPT_DISCUSSION_PROMPT.replace("{research_summary}", summary),
                            end_cmd="/done", label="PPT strategy")
        if result is None:
            return
        tui.ui_task_done("Discuss")

        # ── Phase 6: Framework ──
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

        # ── Phase 7: Debate ──
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

        # ── Phase 8: Style ──
        tui.ui_task_running("Style")
        sp = _load_style(None)
        if sp:
            tui.ui_log(f"  [green]✓[/green] Style loaded: [bold]{sp.name}[/bold]")
        tui.ui_task_done("Style")

        # ── Phase 9: Template ──
        tpl = c.template_path
        if not tpl:
            tui.ui_log("[yellow]![/yellow] [dim]No template configured. Set template_path in ~/.ppt-agent/config.yaml[/dim]")
            tui.ui_task_desc("Enter template path")
            val = tui.get_input(timeout=120)
            if val is None or tui._stop_event.is_set():
                return
            tpl = val
        session.template_path = tpl

        # ── Confirm Generate ──
        if not _confirm(tui, "Generate PPTX?"):
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

        # ── Phase 11: Visual Check ──
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

        # ── Save ──
        tui.ui_task_running("Save")
        session.add_message("system", f"Generated: {output}")
        session.save()
        tui.ui_task_done("Save")
        tui.ui_task_desc("Done")
        tui.ui_log("[dim]─" * 40 + "[/dim]")
        tui.ui_log(f"[green bold]● Done: {output}[/green bold]")

    return run


def run_new_project(config):
    import queue
    set_config(config)
    from ppt_agent.tui import PPTTUI
    app = PPTTUI(queue.Queue())
    app.run()


def run_resume_session(session_path, config):
    import queue
    set_config(config)
    from ppt_agent.tui import PPTTUI
    app = PPTTUI(queue.Queue())
    app.run()
