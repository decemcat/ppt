import click
from pathlib import Path


@click.group()
@click.option("--config", "-c", default=None, help="Config file path")
@click.pass_context
def cli(ctx, config):
    """PPT Agent — Professional technical presentation generator."""
    ctx.ensure_object(dict)
    from ppt_agent.config import load_config
    ctx.obj["config"] = load_config(config)


@cli.command()
@click.argument("topic")
@click.option("--template", "-t", default=None, help="Path to .pptx template")
@click.option("--model", "-m", default=None, help="LLM model override")
@click.option("--no-debate", is_flag=True, help="Skip adversarial discussion")
@click.option("--debate-rounds", default=None, type=int, help="Override debate rounds")
@click.option("--no-visual-check", is_flag=True, help="Skip visual quality check")
@click.option("--style", "style_name", default=None, help="Apply saved style profile")
@click.pass_context
def new(ctx, topic, template, model, no_debate, debate_rounds, no_visual_check, style_name):
    """Start a new PPT project."""
    from ppt_agent.orchestrator import run_new_project
    config = ctx.obj["config"]
    if no_debate:
        config.debate.enabled = False
    if debate_rounds is not None:
        config.debate.max_rounds = debate_rounds
    if no_visual_check:
        config.visual_check.enabled = False
    run_new_project(
        topic=topic,
        config=config,
        template_path=template,
        model_override=model,
        style_name=style_name,
    )


@cli.command()
@click.argument("session_path")
@click.pass_context
def resume(ctx, session_path):
    """Resume an existing session."""
    from ppt_agent.orchestrator import run_resume_session
    run_resume_session(session_path=session_path, config=ctx.obj["config"])


@cli.command("list")
@click.pass_context
def list_sessions(ctx):
    """List all saved sessions."""
    from ppt_agent.session import Session
    sessions_dir = Path.home() / ".ppt-agent" / "sessions"
    if not sessions_dir.exists():
        click.echo("No sessions found.")
        return
    for session_dir in sorted(sessions_dir.iterdir()):
        session_file = session_dir / "session.json"
        if session_file.exists():
            session = Session.load(str(session_file))
            click.echo(f"  {session.created_at[:10]} [{session.session_id}] {session.topic}")


@cli.command()
@click.option("--serve", is_flag=True, help="Start web server instead of CLI")
@click.pass_context
def wiki(ctx, serve):
    """Open LLM Wiki browser."""
    from ppt_agent.research.manager import ResearchManager
    mgr = ResearchManager(ctx.obj["config"])
    mgr.open_wiki(serve=serve)


@cli.command("style-extract")
@click.argument("pptx_path")
@click.option("--name", default="extracted", help="Style profile name")
def style_extract(pptx_path: str, name: str):
    """Extract style profile from a .pptx file."""
    from ppt_agent.style.extractor import StyleExtractor
    profile = StyleExtractor.extract(pptx_path, name)
    path = profile.save()
    click.echo(f"Style profile '{name}' saved to {path}")


@cli.command("style-list")
def style_list():
    """List saved style profiles."""
    from ppt_agent.style.profile import StyleProfile
    profiles = StyleProfile.list_profiles()
    if profiles:
        for p in profiles:
            click.echo(p)
    else:
        click.echo("No style profiles found.")


@cli.command("style-show")
@click.argument("name")
def style_show(name: str):
    """Show details of a style profile."""
    from ppt_agent.style.profile import StyleProfile
    import yaml
    profile = StyleProfile.load(name)
    click.echo(yaml.dump(profile.model_dump(), allow_unicode=True, default_flow_style=False))


def main():
    cli(obj={})


if __name__ == "__main__":
    main()
