"""
The main CLI entry point for readmegen.
Commands:
  readmegen scan <path>      — Phase 1: scan a repo and show results
  readmegen generate <path>  — Full pipeline ()
"""

from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich.prompt import Prompt
from rich import box
 
from ..orchestrator import run_scan, run_generate

# ── App setup ─────────────────────────────────────────────────────────────────

cli = typer.Typer(
    name="readmegen",
    help="AI-powered README generator. Point it at any repo.",
    add_completion=False,
)
console = Console()


TEMPLATES = {
    "1": {
        "key":         "minimal",
        "label":       "Minimal",
        "description": "Title, About, Installation, Usage, License — clean and simple",
        "color":       "dim",
    },
    "2": {
        "key":         "standard",
        "label":       "Standard",
        "description": "All sections with moderate detail — good for most projects",
        "color":       "cyan",
    },
    "3": {
        "key":         "professional",
        "label":       "Professional",
        "description": "Polished, production-quality with horizontal rules and full detail",
        "color":       "green",
    },
    "4": {
        "key":         "detailed",
        "label":       "Detailed",
        "description": "Maximum depth — table of contents, every section, exhaustive",
        "color":       "magenta",
    },
}
 
 
def _select_template() -> str:
    """
    Interactive template selector shown when --template is not passed.
    Returns the chosen template key e.g. "professional".
    """
    console.print()
    console.print("  [bold]Choose a README template:[/bold]")
    console.print()
 
    for num, tmpl in TEMPLATES.items():
        console.print(
            f"  [{tmpl['color']}][bold]{num}[/bold]. {tmpl['label']}[/{tmpl['color']}]"
            f"  [dim]{tmpl['description']}[/dim]"
        )
 
    console.print()
 
    while True:
        choice = Prompt.ask(
            "  [bold cyan]Select[/bold cyan]",
            choices=list(TEMPLATES.keys()),
            default="2",
        )
        tmpl = TEMPLATES.get(choice)
        if tmpl:
            console.print(
                f"\n  [dim]Using[/dim] [bold]{tmpl['label']}[/bold] template.\n"
            )
            return tmpl["key"]

# ── generate ──────────────────────────────────────────────────────────────────
 
@cli.command()
def generate(
    path: Path = typer.Argument(
        default=".",
        help="Path to the repository.",
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o",
        help="Output path for the README. Defaults to <path>/README.md.",
    ),
    template: Optional[str] = typer.Option(
        None, "--template", "-t",
        help="Template style: minimal, standard, professional, detailed. "
             "Skips the interactive selector if provided.",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run",
        help="Preview the README in terminal without writing to disk.",
    ),
    no_cache: bool = typer.Option(
        False, "--no-cache",
        help="Force re-scan and re-analyze even if cached results exist.",
    ),
):
    """
    Generate a README for a repository.
    Runs all three phases: scan → analyze → write.
    """
    root = path.resolve()
    if not root.exists() or not root.is_dir():
        console.print(f"[red]✗[/red] Invalid path: [bold]{root}[/bold]")
        raise typer.Exit(code=1)
 
    valid_keys = {t["key"] for t in TEMPLATES.values()}
 
    if template is not None:
        # Could be a built-in key or a file path
        if template not in valid_keys and not Path(template).exists():
            console.print(
                f"[red]✗[/red] Unknown template: [bold]{template}[/bold]\n"
                f"  Built-in options: {', '.join(sorted(valid_keys))}\n"
                f"  Or pass a path to a custom .md file."
            )
            raise typer.Exit(code=1)
        chosen_template = template
    else:
        chosen_template = _select_template()
 
    # ── Phase 1 ───────────────────────────────────────────────────────────────
    with console.status(
        "[bold cyan]Phase 1[/bold cyan] [dim]scanning repository...[/dim]",
        spinner="dots",
    ):
        from ..orchestrator import run_scan as _scan
        snapshot = _scan(root, use_cache=not no_cache)
 
    frameworks = ", ".join(snapshot.all_frameworks) if snapshot.all_frameworks else "no frameworks detected"
    console.print(
        f"[green]✓[/green] Phase 1 [dim]—[/dim] "
        f"[bold]{snapshot.file_count}[/bold] files  "
        f"[cyan]{snapshot.primary_language}[/cyan]  "
        f"[dim]{frameworks}[/dim]"
    )
 
    # ── Phase 2 ───────────────────────────────────────────────────────────────
    from ..analyzer.router import status as get_backend_status
    bs = get_backend_status()
    backend_label = (
        f"Ollama [dim]({bs['ollama_model']})[/dim]" if bs["will_use"] == "ollama"
        else f"Groq [dim]({bs['groq_model']})[/dim]" if bs["will_use"] == "groq"
        else "[red]no backend configured[/red]"
    )
 
    with console.status(
        f"[bold cyan]Phase 2[/bold cyan] [dim]analyzing with {backend_label}...[/dim]",
        spinner="dots",
    ):
        from ..orchestrator import run_analyze as _analyze
        try:
            analysis = _analyze(snapshot, root, use_cache=not no_cache, template = chosen_template)
        except Exception as e:
            console.print(f"\n[red]✗[/red] Phase 2 failed: {e}\n")
            raise typer.Exit(code=1)
 
    parse_note = (
        "" if analysis.parse_success
        else f" [yellow]⚠ partial parse ({analysis.parse_method})[/yellow]"
    )
    console.print(
        f"[green]✓[/green] Phase 2 [dim]—[/dim] "
        f"analysis complete  "
        f"[dim]method: {analysis.parse_method}[/dim]{parse_note}"
    )
 
    # ── Phase 3 ───────────────────────────────────────────────────────────────
    from ..orchestrator import run_write as _write
    write_result = _write(
        analysis  = analysis,
        snapshot  = snapshot,
        root_path = root,
        output    = output,
        template  = chosen_template,
        dry_run   = dry_run,
    )
 
    if not dry_run:
        console.print(
            f"[green]✓[/green] Phase 3 [dim]—[/dim] "
            f"README written [dim]→[/dim] "
            f"[bold green]{write_result.output_path}[/bold green]  "
            f"[dim]({write_result.line_count} lines)[/dim]"
        )
 
    # ── Summary panel ─────────────────────────────────────────────────────────
    if not dry_run:
        console.print()
        _print_summary(snapshot, analysis, write_result, chosen_template)
 
 
# ── scan ──────────────────────────────────────────────────────────────────────
 
@cli.command()
def scan(
    path: Path = typer.Argument(default=".", help="Path to the repository to scan."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show all collected files."),
    no_cache: bool = typer.Option(False, "--no-cache", help="Force re-scan."),
):
    """Scan a repository and save a snapshot. Phase 1 only."""
    root = path.resolve()
    if not root.exists() or not root.is_dir():
        console.print(f"[red]✗[/red] Invalid path: [bold]{root}[/bold]")
        raise typer.Exit(code=1)
 
    console.print()
    with console.status(
        f"[bold cyan]Phase 1[/bold cyan] [dim]scanning {root.name}...[/dim]",
        spinner="dots",
    ):
        snapshot = run_scan(root, use_cache=not no_cache)
 
    # Summary
    s = Text()
    s.append("  Repo:             ", style="dim"); s.append(f"{snapshot.name}\n", style="bold white")
    s.append("  Primary language: ", style="dim"); s.append(f"{snapshot.primary_language}\n", style="cyan")
    s.append("  Files collected:  ", style="dim")
    s.append(f"{snapshot.file_count}", style="bold green")
    s.append(f"   (skipped {snapshot.skipped_count})\n", style="dim")
    s.append("  Entry points:     ", style="dim")
    s.append(f"{', '.join(snapshot.entry_points) or 'none detected'}\n", style="magenta")
    s.append("  Frameworks:       ", style="dim")
    s.append(f"{', '.join(snapshot.all_frameworks) or 'none detected'}\n", style="bold cyan")
    s.append("  Dependencies:     ", style="dim")
    s.append(f"{len(snapshot.prod_deps)} prod", style="green")
    if snapshot.dev_deps:
        s.append(f"   {len(snapshot.dev_deps)} dev", style="dim")
    
    # Flags Rendering
    flags = [f for f, v in [("Docker", snapshot.has_dockerfile), ("Tests", snapshot.has_tests), ("CI", snapshot.has_ci)] if v]
    if flags:
        s.append("\n  Detected:         ", style="dim")
        for i, f in enumerate(flags):
            s.append(f)
            if i < len(flags) - 1:
                s.append("  ")
        s.stylize("dim", start=s.plain.rfind("Detected:") + 9)

    console.print(Panel(s, title="[bold]Phase 1 — Scan Results[/bold]", border_style="cyan"))
 
    if verbose:
        console.print(Rule("[dim]Collected files[/dim]"))
        t = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold cyan")
        t.add_column("File", style="white"); t.add_column("Language", style="cyan")
        t.add_column("KB", justify="right"); t.add_column("Entry", justify="center")
        for f in snapshot.files:
            t.add_row(f.path, f.language, str(f.size_kb), "[green]✓[/green]" if f.is_entry_point else "")
        console.print(t)
 
    snap_path = root / ".readmegen" / "snapshot.json"
    console.print(f"\n  [dim]Snapshot →[/dim] [green]{snap_path}[/green]")
    console.print(f"\n[green]✓[/green] Phase 1 complete. Run [bold cyan]readmegen generate {path}[/bold cyan] to generate a README.\n")
 
 
# ── status ────────────────────────────────────────────────────────────────────
 
@cli.command()
def status():
    """Check which model backend is available (Ollama or Groq)."""
    from ..analyzer.router import status as get_status
    s = get_status()
    _print_backend_status(s)

def _print_backend_status(s: dict) -> None:
    console.print()
 
    ollama_t = Text()
    if s["ollama_running"]:
        if s["ollama_model_ready"]:
            ollama_t.append("✓ Running", style="green")
            ollama_t.append("  model ")
            ollama_t.append(s["ollama_model"], style="bold")
            ollama_t.append(" ready")
        else:
            ollama_t.append("⚠ Running", style="yellow")
            ollama_t.append("  but ")
            ollama_t.append(s["ollama_model"], style="bold")
            ollama_t.append(" not pulled — run ")
            ollama_t.append(f"ollama pull {s['ollama_model']}", style="cyan")
    else:
        ollama_t.append("✗ Not running", style="dim")
        ollama_t.append("  install at https://ollama.com")

    groq_t = Text()
    if s["groq_available"]:
        groq_t.append("✓ Key found", style="green")
        groq_t.append("  model ")
        groq_t.append(s["groq_model"], style="bold")
    else:
        groq_t.append("✗ No GROQ_API_KEY", style="dim")
        groq_t.append("  get a free key at https://console.groq.com")

    will_use = Text()
    if s["will_use"] == "ollama":
        will_use.append(f"Ollama ({s['ollama_model']})", style="green")
    elif s["will_use"] == "groq":
        will_use.append(f"Groq ({s['groq_model']})", style="cyan")
    else:
        will_use.append("None — configure a backend before running generate", style="red")
 
    t = Text()
    t.append("  Ollama:    ", style="dim"); t.append(ollama_t); t.append("\n")
    t.append("  Groq:      ", style="dim"); t.append(groq_t);   t.append("\n\n")
    t.append("  Will use:  ", style="dim"); t.append(will_use)
    console.print(Panel(t, title="[bold]Backend Status[/bold]", border_style="cyan"))
    console.print()
 
 
# ── Summary panel helper ──────────────────────────────────────────────────────
 
def _print_summary(snapshot, analysis, write_result, chosen_template: Path) -> None:
    """Final summary panel shown after a successful full generate run."""
 
    # Which sections made it into the README
    section_flags = [
        ("About",          bool(analysis.purpose)),
        ("How It Works",   bool(analysis.how_it_works)),
        ("Tech Stack",     bool(analysis.tech_stack)),
        ("Prerequisites",  bool(analysis.prerequisites)),
        ("Installation",   bool(analysis.setup_steps)),
        ("Usage",          bool(analysis.usage_examples)),
        ("Env Variables",  bool(analysis.env_variables)),
        ("API Reference",  bool(analysis.api_endpoints)),
        ("Scripts",        bool(analysis.scripts)),
        ("License",        bool(analysis.license)),
    ]
    included = [name for name, present in section_flags if present]
    skipped  = [name for name, present in section_flags if not present]

    tmpl_label = next(
        (t["label"] for t in TEMPLATES.values() if t["key"] == chosen_template),
        chosen_template,
    )
 
    s = Text()
 
    # Output path
    s.append("  Output:      ", style="dim")
    s.append(f"{write_result.output_path}\n", style="bold green")
 
    # Backup note
    if write_result.backup_path:
        s.append("  Backup:      ", style="dim")
        s.append(f"{write_result.backup_path} ")
        s.append("(previous README)\n", style="dim")

    
    s.append("  Template:    ", style="dim")
    s.append(f"{tmpl_label}\n", style="cyan")
 
    # Size
    s.append("  Size:        ", style="dim")
    s.append(f"{write_result.line_count} lines  {write_result.char_count} chars\n", style="white")
 
    # Sections included
    s.append("  Sections:    ", style="dim")
    s.append(f"{', '.join(included)}\n", style="green")
 
    # Sections skipped (if any)
    if skipped:
        s.append("  Skipped:     ", style="dim")
        s.append(f"{', '.join(skipped)} ")
        s.append("(no data)\n", style="dim")
 
    # Parse quality note
    if not analysis.parse_success:
        s.append("\n  ")
        s.append("⚠", style="yellow")
        s.append("  Partial analysis ")
        s.append(f"(method: {analysis.parse_method})", style="dim")
        s.append(" — review before committing.")
    else:
        s.append("\n  ")
        s.append("✓", style="green")
        s.append("  Analysis parsed cleanly ")
        s.append(f"(method: {analysis.parse_method})", style="dim")
 
    console.print(Panel(
        s,
        title="[bold]Generate Complete[/bold]",
        border_style="green",
    ))
    console.print()


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    cli()

if __name__ == "__main__":
    main()
