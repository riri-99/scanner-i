"""
The main CLI entry point for readmegen.
Commands:
  readmegen scan <path>      — Phase 1: scan a repo and show results
  readmegen generate <path>  — Full pipeline ()
"""

from pathlib import Path
from collections import Counter
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text
from rich.columns import Columns
from rich import box
from typing import Optional

from ..orchestrator import run_scan, run_generate
from ..analyzer.router import status as get_status

# ── App setup ─────────────────────────────────────────────────────────────────

cli = typer.Typer(
    name="readmegen",
    help="AI-powered README generator. Point it at any repo.",
    add_completion=False,
)
console = Console()


# ── scan command ──────────────────────────────────────────────────────────────

@cli.command()
def scan(
    path: Path = typer.Argument(default=".", help="Path to the repository to scan."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show all collected files."),
    no_cache: bool = typer.Option(False, "--no-cache", help="Force re-scan even if snapshot exists."),
):
    
    root = path.resolve()
    if not root.exists()or not root.is_dir():
        console.print(f"[red]✗[/red] Invalid path: [bold]{root}[/bold]")
        raise typer.Exit(code=1)

    console.print()

    with console.status(f"[bold cyan]Phase 1[/bold cyan] [dim] scanning {root.name}...[/dim]", spinner="dots",):
        snapshot = run_scan(root, use_cache=not no_cache)

    _print_snapshot_summary(snapshot, root)
 
    if verbose:
        _print_file_table(snapshot)
 
    snap_path = root / ".readmegen" / "snapshot.json"
    console.print(f"\n  [dim]Snapshot →[/dim] [green]{snap_path}[/green]")
    console.print(
        f"\n[green]✓[/green] Phase 1 complete. "
        f"Run [bold cyan]readmegen generate {path}[/bold cyan] to analyze.\n"
    )


# ── generate command ──────────────────────────────────────────────────────────

@cli.command()

def generate(
    path: Path = typer.Argument(default=".", help="Path to the repository."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output path for README."),
    no_cache: bool = typer.Option(False, "--no-cache", help="Force re-scan and re-analyze."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print analysis to terminal, no files written."),
):
    root = path.resolve()
    if not root.exists() or not root.is_dir():
        console.print(f"[red]✗[/red] Invalid path: [bold]{root}[/bold]")
        raise typer.Exit(code=1)

    console.print()

    # ── Phase 1 ───────────────────────────────────────────────────────────────
    with console.status(
        "[bold cyan]Phase 1[/bold cyan] [dim]scanning repository...[/dim]",
        spinner="dots",
    ):
        from ..orchestrator import run_scan as _scan
        snapshot = _scan(root, use_cache=not no_cache)
 
    console.print(
        f"[green]✓[/green] Phase 1 — "
        f"[bold]{snapshot.file_count}[/bold] files  "
        f"[bold]{snapshot.primary_language}[/bold]  "
        f"[bold]{', '.join(snapshot.all_frameworks) or 'no frameworks detected'}[/bold]"
    )
 
    # ── Phase 2 ───────────────────────────────────────────────────────────────
    from ..analyzer.router import status as backend_status
    bs = backend_status()
    backend_label = (
        f"Ollama [dim]({bs['ollama_model']})[/dim]" if bs["will_use"] == "ollama"
        else f"Groq [dim]({bs['groq_model']})[/dim]"   if bs["will_use"] == "groq"
        else "no backend"
    )
 
    with console.status(
        f"[bold cyan]Phase 2[/bold cyan] [dim]analyzing with {backend_label}...[/dim]",
        spinner="dots",
    ):
        from ..orchestrator import run_analyze as _analyze
        try:
            analysis = _analyze(snapshot, root, use_cache=not no_cache)
        except Exception as e:
            console.print(f"\n[red]✗[/red] Phase 2 failed: {e}\n")
            raise typer.Exit(code=1)
 
    # ── Phase 2 result ────────────────────────────────────────────────────────
    parse_indicator = (
        "[green]✓[/green]" if analysis.parse_success
        else f"[yellow]⚠[/yellow] [dim](partial — method: {analysis.parse_method})[/dim]"
    )
    console.print(
        f"{parse_indicator} Phase 2 — analysis complete  "
        f"[dim]method: {analysis.parse_method}[/dim]"
    )
 
    console.print()
 
    # ── Analysis panel ────────────────────────────────────────────────────────
    _print_analysis_summary(analysis, dry_run)
 
    # ── Saved paths ───────────────────────────────────────────────────────────
    if not dry_run:
        snap_path     = root / ".readmegen" / "snapshot.json"
        analysis_path = root / ".readmegen" / "analysis.json"
        console.print(f"\n  [dim]Snapshot  →[/dim] [green]{snap_path}[/green]")
        console.print(f"  [dim]Analysis  →[/dim] [green]{analysis_path}[/green]")
 
    console.print(
        "\n[yellow]⚠[/yellow]  Phase 3 (README writer) coming next. "
        "Analysis saved — nothing written yet.\n"
    )


# ── Status Command ───────────────────────────────────────────────────────────────

@cli.command()

def status():
    s = get_status()
    console.print()

    # Plain-text status (no color markup)
    if s["ollama_running"] and s["ollama_model_ready"]:
        ollama_status = f"✓ Running — model {s['ollama_model']} ready"
    elif s["ollama_running"]:
        ollama_status = f"⚠ Running — but {s['ollama_model']} not pulled — run 'ollama pull {s['ollama_model']}'"
    else:
        ollama_status = "✗ Not running — install at https://ollama.com"

    groq_status = (
        f"✓ Key found — model {s['groq_model']}"
        if s["groq_available"]
        else "✗ No GROQ_API_KEY — get a free key at https://console.groq.com"
    )

    will_use_label = {
        "ollama": f"Ollama ({s['ollama_model']})",
        "groq":   f"Groq ({s['groq_model']})",
        "none":   "None — configure a backend before running generate",
    }[s["will_use"]]

    t = Text()
    t.append("  Ollama:    ", style="dim"); t.append(ollama_status + "\n")
    t.append("  Groq:      ", style="dim"); t.append(groq_status   + "\n\n")
    t.append("  Will use:  ", style="dim"); t.append(will_use_label)

    console.print(Panel(t, title="Backend Status", border_style="cyan"))
    console.print()

# DISPLAY HELPERS

def _print_snapshot_summary(snapshot, root: Path) -> None:
    s = Text()
    s.append("  Repo:             ", style="dim")
    s.append(f"{snapshot.name}\n", style="bold white")
    s.append("  Primary language: ", style="dim")
    s.append(f"{snapshot.primary_language}\n", style="cyan")
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
    flags = []
    if snapshot.has_dockerfile: flags.append("Docker")
    if snapshot.has_tests:      flags.append("Tests")
    if snapshot.has_ci:         flags.append("CI")
    if flags:
        s.append("\n  Detected:         ", style="dim")
        s.append("  ".join(f"[dim]{f}[/dim]" for f in flags))
    console.print(Panel(s, title="[bold]Phase 1 — Scan Results[/bold]", border_style="cyan"))
 
 
def _print_analysis_summary(analysis, dry_run: bool) -> None:
    s = Text()
 
    s.append("  Purpose:      ", style="dim")
    s.append(f"{analysis.purpose or '—'}\n", style="white")
 
    s.append("  How it works: ", style="dim")
    s.append(f"{analysis.how_it_works or '—'}\n", style="dim white")
 
    if analysis.tech_stack:
        s.append("  Tech stack:   ", style="dim")
        s.append(f"{', '.join(analysis.tech_stack)}\n", style="cyan")
 
    if analysis.prerequisites:
        s.append("  Prerequisites:", style="dim")
        s.append(f" {', '.join(analysis.prerequisites)}\n")
 
    if analysis.setup_steps:
        s.append("  Setup steps:  ", style="dim")
        s.append(f"{len(analysis.setup_steps)} steps\n", style="green")
 
    if analysis.env_variables:
        s.append("  Env vars:     ", style="dim")
        names = [e.get("name", "") for e in analysis.env_variables]
        s.append(f"{', '.join(names)}\n", style="yellow")
 
    if analysis.api_endpoints:
        s.append("  API endpoints:", style="dim")
        s.append(f" {len(analysis.api_endpoints)} detected\n")
 
    if analysis.license:
        s.append("  License:      ", style="dim")
        s.append(f"{analysis.license}\n")
 
    console.print(Panel(s, title="[bold]Phase 2 — Analysis Results[/bold]", border_style="green"))
 
    # Setup steps detail
    if analysis.setup_steps and dry_run:
        console.print(Rule("[dim]Setup steps[/dim]"))
        for i, step in enumerate(analysis.setup_steps, 1):
            console.print(f"  [dim]{i}.[/dim] {step}")
 
 
def _print_file_table(snapshot) -> None:
    console.print(Rule("[dim]Collected files[/dim]"))
    t = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold cyan")
    t.add_column("File", style="white")
    t.add_column("Language", style="cyan")
    t.add_column("KB", justify="right")
    t.add_column("Entry", justify="center")
    for f in snapshot.files:
        t.add_row(
            f.path, f.language, str(f.size_kb),
            "[green]✓[/green]" if f.is_entry_point else "",
        )
    console.print(t)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    cli()

if __name__ == "__main__":
    main()

