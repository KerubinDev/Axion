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

# Load environment variables from .env file
load_dotenv()

app = typer.Typer(
    name="akita",
    help="AkitaLLM: Local-first AI orchestrator for programmers.",
    add_completion=False,
)
console = Console()

@app.callback()
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

    # Onboarding check
    if not CONFIG_FILE.exists():
        run_onboarding()

def run_onboarding():
    console.print(Panel(
        "[bold cyan]AkitaLLM Configuration[/]\n\n[italic]API-first setup...[/]",
        title="Onboarding"
    ))
    
    api_key = typer.prompt("🔑 Paste your API Key (or type 'ollama' for local)", hide_input=False)
    
    provider = detect_provider(api_key)
    if not provider:
        console.print("[bold red]❌ Could not detect provider from the given key.[/]")
        console.print("Make sure you are using a valid OpenAI (sk-...) or Anthropic (sk-ant-...) key.")
        raise typer.Abort()

    console.print(f"[bold green]✅ Detected Provider:[/] {provider.name.upper()}")
    
    with console.status(f"[bold blue]Consulting {provider.name} API for available models..."):
        try:
            models = provider.list_models(api_key)
        except Exception as e:
            console.print(f"[bold red]❌ Failed to list models:[/] {e}")
            raise typer.Abort()
    
    if not models:
        console.print("[bold yellow]⚠️ No models found for this provider.[/]")
        raise typer.Abort()

    console.print("\n[bold]Select a model:[/]")
    for i, model in enumerate(models):
        name_display = f" ({model.name})" if model.name else ""
        console.print(f"{i+1}) [cyan]{model.id}[/]{name_display}")
    
    choice = typer.prompt("\nChoose a model number", type=int, default=1)
    if 1 <= choice <= len(models):
        selected_model = models[choice-1].id
    else:
        console.print("[bold red]Invalid choice.[/]")
        raise typer.Abort()

    # Determine if we should save the key or use an env ref
    use_env = typer.confirm("Would you like to use an environment variable for the API key? (Recommended)", default=True)
    
    final_key_ref = api_key
    if use_env and provider.name != "ollama":
        env_var_name = f"{provider.name.upper()}_API_KEY"
        console.print(f"[dim]Please ensure you set [bold]{env_var_name}[/] in your .env or shell.[/]")
        final_key_ref = f"env:{env_var_name}"

    config = {
        "model": {
            "provider": provider.name,
            "name": selected_model,
            "api_key": final_key_ref
        }
    }
    
    save_config(config)
    console.print(f"\n[bold green]✨ Configuration saved![/]")
    console.print(f"Model: [bold]{selected_model}[/]")
    console.print(f"Key reference: [dim]{final_key_ref}[/]")
    console.print("\n[dim]Configuration stored at ~/.akita/config.toml[/]\n")

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
    query: str,
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Run in interactive mode to refine the solution."),
    trace: bool = typer.Option(False, "--trace", help="Show the internal reasoning trace."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Run in dry-run mode.")
):
    """
    Generate and apply a solution for the given query.
    """
    model = get_model()
    engine = ReasoningEngine(model)
    console.print(Panel(f"[bold blue]Akita[/] is thinking about: [italic]{query}[/]", title="Solve Mode"))
    
    current_query = query
    session = None
    
    try:
        while True:
            diff_output = engine.run_solve(current_query, session=session)
            session = engine.session
            
            if trace:
                console.print(Panel(str(engine.trace), title="[bold cyan]Reasoning Trace[/]", border_style="cyan"))
            console.print(Panel("[bold green]Suggested Code Changes (Unified Diff):[/]"))
            syntax = Syntax(diff_output, "diff", theme="monokai", line_numbers=True)
            console.print(syntax)
            
            if interactive:
                action = typer.prompt("\n[A]pprove, [R]efine with feedback, or [C]ancel?", default="A").upper()
                if action == "A":
                    break
                elif action == "R":
                    current_query = typer.prompt("Enter your feedback/refinement")
                    continue
                else:
                    console.print("[yellow]Operation cancelled.[/]")
                    return
            else:
                break

        if not dry_run:
            confirm = typer.confirm("\nDo you want to apply these changes?")
            if confirm:
                console.print("[bold yellow]🚀 Applying changes...[/]")
                success = DiffApplier.apply_unified_diff(diff_output)
                if success:
                    console.print("[bold green]✅ Changes applied successfully![/]")
                else:
                    console.print("[bold red]❌ Failed to apply changes.[/]")
            else:
                console.print("[bold yellow]Changes discarded.[/]")
    except Exception as e:
        console.print(f"[bold red]Solve failed:[/] {e}")
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

@config_app.command("model")
def config_model(
    reset: bool = typer.Option(False, "--reset", help="Reset configuration to defaults.")
):
    """
    View or change the model configuration.
    """
    if reset:
        if typer.confirm("Are you sure you want to delete your configuration?"):
            reset_config()
            console.print("[bold green]✅ Configuration reset. Onboarding will run on next command.[/]")
        return

    config = load_config()
    if not config:
        console.print("[yellow]No configuration found. Running setup...[/]")
        run_onboarding()
        config = load_config()

    console.print(Panel(
        f"[bold blue]Current Model Configuration[/]\n\n"
        f"Provider: [yellow]{config['model']['provider']}[/]\n"
        f"Name: [yellow]{config['model']['name']}[/]",
        title="Settings"
    ))
    
    if typer.confirm("Do you want to change these settings?"):
        run_onboarding()

if __name__ == "__main__":
    app()
