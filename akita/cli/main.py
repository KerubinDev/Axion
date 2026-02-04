import typer
from typing import Optional, List, Dict, Any
from rich.console import Console
from rich.panel import Panel
from akita.reasoning.engine import ReasoningEngine
from akita.core.indexing import CodeIndexer
from akita.models.base import get_model
from akita.core.config import load_config, save_config, reset_config, CONFIG_FILE
from rich.table import Table
from rich.markdown import Markdown
from rich.syntax import Syntax
from dotenv import load_dotenv
from akita.tools.diff import DiffApplier
from akita.tools.git import GitTool
from akita.core.providers import detect_provider
from akita.core.i18n import t

# Load environment variables from .env file
load_dotenv()

app = typer.Typer(
    name="akita",
    help="AkitaLLM: Local-first AI orchestrator for programmers.",
    add_completion=False,
)
console = Console()

@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    dry_run: bool = typer.Option(False, "--dry-run", help="Run without making any changes.")
):
    """
    AkitaLLM orchestrates LLMs to help you code with confidence.
    """
    # Skip onboarding for the config command itself
    if ctx.invoked_subcommand == "config":
        return

    if dry_run:
        console.print("[bold yellow]⚠️ Running in DRY-RUN mode. No changes will be applied.[/]")

    # Proactive Onboarding / Welcome Logic
    if not CONFIG_FILE.exists():
        # If no config, always run onboarding (except for help/version which are handled by Typer earlier)
        run_onboarding()
        # After onboarding, if it was a bare command, show welcome
        if ctx.invoked_subcommand is None:
            console.print(Panel(
                f"{t('welcome.subtitle')}\n\n{t('welcome.commands')}\n\n{t('welcome.help_hint')}",
                title=t("welcome.title")
            ))
    elif ctx.invoked_subcommand is None:
        # Config exists, bare command -> Show Welcome Banner
        console.print(Panel(
            f"{t('welcome.subtitle')}\n\n{t('welcome.commands')}\n\n{t('welcome.help_hint')}",
            title=t("welcome.title")
        ))


def run_onboarding():
    console.print(Panel(
        t("onboarding.welcome"),
        title="Onboarding"
    ))
    
    api_key = typer.prompt(t("onboarding.api_key_prompt"), hide_input=False)
    
    provider = detect_provider(api_key)
    if not provider:
        console.print("[bold red]❌ Could not detect provider from the given key.[/]")
        console.print("Make sure you are using a valid OpenAI (sk-...) or Anthropic (sk-ant-...) key.")
        raise typer.Abort()

    console.print(t("onboarding.provider_detected", provider=provider.name.upper()))
    
    with console.status(t("onboarding.models_consulting", provider=provider.name)):
        try:
            models = provider.list_models(api_key)
        except Exception as e:
            console.print(t("onboarding.models_failed", error=e))
            raise typer.Abort()
    
    if not models:
        console.print(t("onboarding.no_models"))
        raise typer.Abort()

    console.print(t("onboarding.select_model"))
    for i, model in enumerate(models):
        name_display = f" ({model.name})" if model.name else ""
        console.print(f"{i+1}) [cyan]{model.id}[/]{name_display}")
    
    choice = typer.prompt(t("onboarding.choice_prompt"), type=int, default=1)
    if 1 <= choice <= len(models):
        selected_model = models[choice-1].id
    else:
        console.print(t("onboarding.invalid_choice"))
        raise typer.Abort()

    # New: Preferred Language for UI (Visual Sync Test)
    lang_choice = typer.prompt(t("onboarding.lang_choice"), default="en")

    # New: Creativity (Temperature) setting
    creativity = typer.prompt(t("onboarding.creativity_prompt"), default=0.7, type=float)

    # Determine if we should save the key or use an env ref
    use_env = typer.confirm(t("onboarding.env_confirm"), default=True)
    
    final_key_ref = api_key
    if use_env and provider.name != "ollama":
        env_var_name = f"{provider.name.upper()}_API_KEY"
        console.print(t("onboarding.env_instruction", env_var=env_var_name))
        final_key_ref = f"env:{env_var_name}"

    config = {
        "model": {
            "provider": provider.name,
            "name": selected_model,
            "api_key": final_key_ref,
            "language": lang_choice,
            "temperature": creativity
        }
    }
    
    save_config(config)
    console.print(t("onboarding.saved"))
    console.print(f"Model: [bold]{selected_model}[/]")
    console.print(f"Key reference: [dim]{final_key_ref}[/]")
    console.print(t("onboarding.saved_location", path="~/.akita/config.toml"))

@app.command()
def review(
    path: str = typer.Argument(".", help="Path to review."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Run in dry-run mode.")
):
    """
    Review code in the specified path.
    """
    model = get_model()
    engine = ReasoningEngine(model)
    console.print(Panel(f"[bold blue]Akita[/] is reviewing: [yellow]{path}[/]", title="Review Mode"))
    
    if dry_run:
        console.print("[yellow]Dry-run: Context would be built and LLM would be called.[/]")
        return

    try:
        result = engine.run_review(path)
        
        # Display Results
        console.print(Panel(result.summary, title="[bold blue]Review Summary[/]"))
        
        if result.issues:
            table = Table(title="[bold red]Identified Issues[/]", show_header=True, header_style="bold magenta")
            table.add_column("File")
            table.add_column("Type")
            table.add_column("Description")
            table.add_column("Severity")
            
            for issue in result.issues:
                color = "red" if issue.severity == "high" else "yellow" if issue.severity == "medium" else "blue"
                table.add_row(issue.file, issue.type, issue.description, f"[{color}]{issue.severity}[/]")
            
            console.print(table)
        else:
            console.print("[bold green]No issues identified! ✨[/]")

        if result.strengths:
            console.print("\n[bold green]💪 Strengths:[/]")
            for s in result.strengths:
                console.print(f"  - {s}")

        if result.suggestions:
            console.print("\n[bold cyan]💡 Suggestions:[/]")
            for s in result.suggestions:
                console.print(f"  - {s}")

        color = "red" if result.risk_level == "high" else "yellow" if result.risk_level == "medium" else "green"
        console.print(Panel(f"Resulting Risk Level: [{color} bold]{result.risk_level.upper()}[/]", expand=False))

    except Exception as e:
        console.print(f"[bold red]Review failed:[/] {e}")
        raise typer.Exit(code=1)

@app.command()
def solve(
    query: Optional[str] = typer.Argument(None, help="The task for Akita to solve."),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Run in interactive mode to refine the solution."),
    trace: bool = typer.Option(False, "--trace", help="Show the internal reasoning trace."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Run in dry-run mode.")
):
    """
    Generate and apply a solution for the given query.
    """
    # Interactive Input if no query provided
    if not query:
        console.print(t("solve.input_prompt"))
        lines = []
        try:
            while True:
                line = input()
                lines.append(line)
        except EOFError:
            pass
        query = "\n".join(lines).strip()
        
        if not query:
            console.print("[yellow]Empty query. Exiting.[/]")
            raise typer.Exit()

    model = get_model()
    engine = ReasoningEngine(model)
    console.print(Panel(f"[bold blue]Akita[/] is thinking about: [italic]{query}[/]", title=t("solve.mode_title")))
    
    current_query = query
    session = None
    
    try:
        while True:
            # Pass interactive session if reusing context
            diff_output = engine.run_solve(current_query, session=session)
            session = engine.session
            
            if trace:
                console.print(Panel(str(engine.trace), title=t("solve.trace_title"), border_style="cyan"))
            
            console.print(Panel(t("solve.diff_title")))
            syntax = Syntax(diff_output, "diff", theme="monokai", line_numbers=True)
            console.print(syntax)
            
            # If explicit interactive flag OR we just captured input interactively, we probably want to offer refinement?
            # The spec said "interactive solve", usually implies refinement loop.
            # Let's keep the logic: if --interactive flag is used, prompt.
            if interactive:
                action = typer.prompt(t("solve.interactive_prompt"), default="A").upper()
                if action == "A":
                    break
                elif action == "R":
                    current_query = typer.prompt(t("solve.refine_prompt"))
                    continue
                else:
                    console.print(t("solve.cancelled"))
                    return
            else:
                break

        if not dry_run:
            confirm = typer.confirm(t("solve.confirm_apply"))
            if confirm:
                console.print(t("solve.applying"))
                success = DiffApplier.apply_unified_diff(diff_output)
                if success:
                    console.print(t("solve.success"))
                else:
                    console.print(t("solve.failed"))
            else:
                console.print(t("solve.discarded"))
    except Exception as e:
        console.print(t("error.solve_failed", error=e))
        raise typer.Exit(code=1)

@app.command()
def plan(
    goal: str,
    dry_run: bool = typer.Option(False, "--dry-run", help="Run in dry-run mode.")
):
    """
    Generate a step-by-step plan for a goal.
    """
    model = get_model()
    engine = ReasoningEngine(model)
    console.print(Panel(f"[bold blue]Akita[/] is planning: [yellow]{goal}[/]", title="Plan Mode"))
    
    try:
        plan_output = engine.run_plan(goal)
        console.print(Markdown(plan_output))
    except Exception as e:
        console.print(f"[bold red]Planning failed:[/] {e}")
        raise typer.Exit(code=1)

@app.command()
def clone(
    url: str = typer.Argument(..., help="Git repository URL to clone."),
    branch: Optional[str] = typer.Option(None, "--branch", "-b", help="Specific branch to clone."),
    depth: Optional[int] = typer.Option(None, "--depth", "-d", help="Create a shallow clone with a history truncated to the specified number of commits.")
):
    """
    Clone a remote Git repository into the Akita workspace (~/.akita/repos/).
    """
    console.print(Panel(f"🌐 [bold blue]Akita[/] is cloning: [yellow]{url}[/]", title="Clone Mode"))
    
    try:
        with console.status("[bold green]Cloning repository..."):
            local_path = GitTool.clone_repo(url, branch=branch, depth=depth)
        
        console.print(f"\n[bold green]✅ Repository cloned successfully![/]")
        console.print(f"📍 Local path: [cyan]{local_path}[/]")
    except FileExistsError as e:
        console.print(f"[bold yellow]⚠️ {e}[/]")
    except Exception as e:
        console.print(f"[bold red]❌ Clone failed:[/] {e}")
        raise typer.Exit(code=1)

@app.command()
def index(
    path: str = typer.Argument(".", help="Path to index for RAG.")
):
    """
    Build a local vector index (RAG) for the project.
    """
    console.print(Panel(f"🔍 [bold blue]Akita[/] is indexing: [yellow]{path}[/]", title="Index Mode"))
    try:
        indexer = CodeIndexer(path)
        with console.status("[bold green]Indexing project files..."):
            indexer.index_project()
        console.print("[bold green]✅ Indexing complete! Semantic search is now active.[/]")
    except Exception as e:
        console.print(f"[bold red]Indexing failed:[/] {e}")
        raise typer.Exit(code=1)

@app.command()
def test():
    """
    Run automated tests in the project.
    """
    console.print(Panel("[bold blue]Akita[/] is running tests...", title="Test Mode"))
    from akita.tools.base import ShellTools
    result = ShellTools.execute("pytest")
    if result.success:
        console.print("[bold green]Tests passed![/]")
        console.print(result.output)
    else:
        console.print("[bold red]Tests failed![/]")
        console.print(result.error or result.output)

@app.command()
def docs():
    """
    Start the local documentation server.
    """
    import subprocess
    import sys
    
    console.print(Panel("[bold blue]Akita[/] Documentation", title="Docs Mode"))
    console.print("[dim]Starting MkDocs server...[/]")
    console.print("[bold green]Open your browser at: http://127.0.0.1:8000[/]")
    
    try:
        subprocess.run([sys.executable, "-m", "mkdocs", "serve"], check=True)
    except FileNotFoundError:
        console.print("[red]MkDocs not found. Install it with: pip install mkdocs-material[/]")
        raise typer.Exit(code=1)
    except KeyboardInterrupt:
        console.print("[yellow]Documentation server stopped.[/]")

# Config Command Group
config_app = typer.Typer(help="Manage AkitaLLM configuration.")
app.add_typer(config_app, name="config")

@config_app.callback(invoke_without_command=True)
def main_config(ctx: typer.Context):
    """
    Manage AkitaLLM configuration via interactive menu.
    """
    if ctx.invoked_subcommand:
        return

    while True:
        console.print(Panel(
            f"{t('config.menu.option.model')}\n"
            f"{t('config.menu.option.language')}\n"
            f"{t('config.menu.option.show')}\n"
            f"{t('config.menu.option.exit')}",
            title=t("config.menu.title")
        ))
        
        choice = typer.prompt(t("config.menu.prompt"), default="3")
        
        if choice == "1":
            # Model
            if typer.confirm("Re-run model setup setup?"):
                run_onboarding()
        elif choice == "2":
            # Language
            lang = typer.prompt(t("onboarding.lang_choice"), default="en")
            config = load_config() or {}
            if "model" not in config: config["model"] = {}
            config["model"]["language"] = lang
            save_config(config)
            console.print(t("onboarding.saved"))
        elif choice == "3":
            # Show
            config = load_config()
            if not config:
                console.print("[yellow]No config.[/]")
                continue
            console.print(Panel(
                f"Provider: [yellow]{config.get('model', {}).get('provider')}[/]\n"
                f"Name: [yellow]{config.get('model', {}).get('name')}[/]\n"
                f"Language: [yellow]{config.get('model', {}).get('language')}[/]",
                title=t("config.current_title")
            ))
            typer.prompt("Press Enter to continue")
        elif choice == "4":
            break
        else:
            console.print(t("onboarding.invalid_choice"))

@config_app.command("model")
def config_model_legacy():
    """Legacy command for scripting."""
    run_onboarding()

if __name__ == "__main__":
    app()
