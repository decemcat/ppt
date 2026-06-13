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
@click.pass_context
def new(ctx, topic, template, model):
    """Start a new PPT project."""
    from ppt_agent.orchestrator import run_new_project
    run_new_project(
        topic=topic,
        config=ctx.obj["config"],
        template_path=template,
        model_override=model,
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


def main():
    cli(obj={})


if __name__ == "__main__":
    main()
