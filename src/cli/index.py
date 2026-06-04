"""
The main CLI entry point for readmegen.
Commands:
  readmegen scan <path>      — Phase 1: scan a repo and show results
  readmegen generate <path>  — Full pipeline (Phase 2+3 stubbed for now)
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

    with console.status(f"[bold cyan]Scanning[/bold cyan] [dim]{root}[/dim]...", spinner="dots",):
        snapshot = run_scan(root, use_cache=not no_cache)


    # Summary panel 
    s = Text()
 
    s.append("  Repo:             ", style="dim")
    s.append(f"{snapshot.name}\n", style="bold white")
 
    s.append("  Primary language: ", style="dim")
    s.append(f"{snapshot.primary_language}\n", style="bold cyan")
 
    s.append("  All languages:    ", style="dim")
    s.append(f"{', '.join(snapshot.languages) or 'none'}\n", style="cyan")
 
    s.append("  Files collected:  ", style="dim")
    s.append(f"{snapshot.file_count}", style="bold green")
    s.append(f"   (skipped {snapshot.skipped_count})\n", style="dim")
 
    s.append("  Entry points:     ", style="dim")
    s.append(f"{', '.join(snapshot.entry_points) or 'none detected'}\n", style="magenta")
 
    s.append("  Ecosystems:       ", style="dim")
    ecosystems = [e.ecosystem for e in snapshot.ecosystems]
    s.append(f"{', '.join(ecosystems) or 'none detected'}\n", style="cyan")
 
    s.append("  Frameworks:       ", style="dim")
    s.append(f"{', '.join(snapshot.all_frameworks) or 'none detected'}\n", style="bold cyan")
 
    s.append("  Dependencies:     ", style="dim")
    s.append(f"{len(snapshot.prod_deps)} prod", style="green")
    if snapshot.dev_deps:
        s.append(f"   {len(snapshot.dev_deps)} dev", style="dim")
    s.append("\n")


    # Flags row
    flags = []
    if snapshot.has_dockerfile: flags.append("[dim]Docker[/dim]")
    if snapshot.has_tests:      flags.append("[dim]Tests[/dim]")
    if snapshot.has_ci:         flags.append("[dim]CI[/dim]")
    if flags:
        s.append("  Detected:         ", style="dim")
        s.append("  ".join(flags) + "\n")
 
    console.print(Panel(s, title="[bold]Scan Results[/bold]", border_style="cyan"))


    # Dependency tables
    if snapshot.ecosystems:
        console.print()
        for eco in snapshot.ecosystems:
            prod = [d for d in eco.dependencies if not d.is_dev]
            dev  = [d for d in eco.dependencies if d.is_dev]
 
            console.print(
                f"  [bold]{eco.ecosystem}[/bold] [dim]via {eco.source_file}[/dim]"
                + (f"  [dim]scripts: {', '.join(eco.scripts.keys())}[/dim]" if eco.scripts else "")
            )
 
            t = Table(box=box.SIMPLE, show_header=True, header_style="dim", padding=(0, 1))
            t.add_column("Package")
            t.add_column("Version", style="dim")
            t.add_column("", style="dim")   # prod / dev label
 
            for d in prod[:15]:
                t.add_row(d.name, d.version or "—", "prod")
            for d in dev[:5]:
                t.add_row(f"[dim]{d.name}[/dim]", d.version or "—", "dev")
            if len(prod) > 15:
                t.add_row(f"[dim]… +{len(prod) - 15} more[/dim]", "", "")
 
            console.print(t)

    # Verbose: full file list 
    if verbose:
        console.print(Rule("[dim]Collected files[/dim]"))
        t = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold cyan")
        t.add_column("File", style="white")
        t.add_column("Language", style="cyan")
        t.add_column("KB", justify="right")
        t.add_column("Entry", justify="center")
        t.add_column("Trunc", justify="center")
 
        for f in snapshot.files:
            t.add_row(
                f.path,
                f.language,
                str(f.size_kb),
                "[green]✓[/green]" if f.is_entry_point else "",
                "[yellow]⚠[/yellow]" if f.is_truncated else "",
            )
        console.print(t)

    # Footer
    snap_path = root / ".readmegen" / "snapshot.json"
    console.print(f"\n  [dim]Snapshot saved →[/dim] [green]{snap_path}[/green]")
    console.print(
        f"\n[green]✓[/green] Phase 1 complete. "
        f"Run [bold cyan]readmegen generate {path}[/bold cyan] to produce a README.\n"
    )    


# ── generate command ──────────────────────────────────────────────────────────

@cli.command()

def generate(
    path: Path = typer.Argument(default=".", help="Path to the repository."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output path for the README."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print to terminal instead of writing a file."),
    no_cache: bool = typer.Option(False, "--no-cache", help="Force re-scan even if snapshot exists."),
):
    """
    Generate a README for a repository (full pipeline).
    Phase 2 and 3 are coming — currently runs Phase 1 only.
    """
    root = path.resolve()
    if not root.exists() or not root.is_dir():
        console.print(f"[red]✗[/red] Invalid path: [bold]{root}[/bold]")
        raise typer.Exit(code=1)

    console.print()
    console.print(Panel(
        "[yellow]⚠[/yellow]  Phase 2 (AI analysis) and Phase 3 (README writing) "
        "are not built yet.\nRunning Phase 1 scan only for now.",
        border_style="yellow",
    ))
    console.print()

    with console.status("[bold cyan]Scanning repository...[/bold cyan]", spinner="dots"):
        snapshot = run_generate(root)

    console.print(
        f"[green]✓[/green] Scanned [bold]{snapshot.file_count}[/bold] files  "
        f"[bold]{len(snapshot.all_frameworks)}[/bold] frameworks  "
        f"[bold]{len(snapshot.prod_deps)}[/bold] dependencies\n"
        f"[dim]Snapshot → {root / '.readmegen' / 'snapshot.json'}[/dim]\n"
    )


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    cli()

if __name__ == "__main__":
    main()