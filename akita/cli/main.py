import typer
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
        "[bold cyan]AkitaLLM[/]\n\n[italic]Understanding the internals...[/]",
        title="Onboarding"
    ))
    
    console.print("1) Use default project model (GPT-4o Mini)")
    console.print("2) Configure my own model")
    
    choice = typer.prompt("\nChoose an option", type=int, default=1)
    
    if choice == 1:
        config = {"model": {"provider": "openai", "name": "gpt-4o-mini"}}
        save_config(config)
        console.print("[bold green]✅ Default model (GPT-4o Mini) selected and saved![/]")
    else:
        provider = typer.prompt("Enter model provider (e.g., openai, ollama, anthropic)", default="openai")
        name = typer.prompt("Enter model name (e.g., gpt-4o, llama3, claude-3-opus)", default="gpt-4o-mini")
        config = {"model": {"provider": provider, "name": name}}
        save_config(config)
        console.print(f"[bold green]✅ Model configured: {provider}/{name}[/]")
    
    console.print("\n[dim]Configuration saved at ~/.akita/config.toml[/]\n")

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
