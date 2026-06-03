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
from rich.text import Text
from rich import box
from typing import Optional

from ..orchestrator import run_scan, run_generate

#  App setup 

app = Console()
cli = typer.Typer(
    name="readmegen",
    help="AI-powered README generator. Point it at any repo.",
    add_completion=False,
)
console = Console()


#  scan command 

@cli.command()
def scan(
    path: Path = typer.Argument(
        default=".",
        help="Path to the repository to scan.",
        show_default=True,
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v",
        help="Show every file collected.",
    ),
):
    """
    Scan a repository and display what was found.
    This runs Phase 1 only — no README is generated.
    """
    #  Validate path 
    root = path.resolve()
    if not root.exists():
        console.print(f"[red]✗[/red] Path does not exist: [bold]{root}[/bold]")
        raise typer.Exit(code=1)
    if not root.is_dir():
        console.print(f"[red]✗[/red] Path is not a directory: [bold]{root}[/bold]")
        raise typer.Exit(code=1)

    #  Run scan 
    console.print()
    with console.status(
        f"[bold cyan]Scanning[/bold cyan] [dim]{root}[/dim]...",
        spinner="dots",
    ):
        result = run_scan(root)

    #  Summary panel 
    lang_counts = Counter(f.language for f in result.files)
    top_langs   = ", ".join(
        f"{lang} ({count})" for lang, count in lang_counts.most_common(5)
    )
    entry_points = [f.path for f in result.files if f.is_entry_point]
    truncated    = sum(1 for f in result.files if f.is_truncated)

    summary = Text()
    summary.append(f"  Repo:          ", style="dim")
    summary.append(f"{root.name}\n",     style="bold white")

    summary.append(f"  Files found:   ", style="dim")
    summary.append(f"{len(result.files)}\n", style="bold green")

    summary.append(f"  Files skipped: ", style="dim")
    summary.append(f"{result.skipped_count}\n", style="yellow")

    summary.append(f"  Languages:     ", style="dim")
    summary.append(f"{top_langs or 'none detected'}\n", style="cyan")

    summary.append(f"  Entry points:  ", style="dim")
    summary.append(f"{', '.join(entry_points) or 'none detected'}\n", style="magenta")

    if truncated:
        summary.append(f"  Truncated:     ", style="dim")
        summary.append(f"{truncated} files (content too large)\n", style="yellow")

    console.print(Panel(summary, title="[bold]Scan Results[/bold]", border_style="cyan"))

    #  File table (only with --verbose) 
    if verbose:
        table = Table(
            box=box.SIMPLE_HEAD,
            show_header=True,
            header_style="bold cyan",
            row_styles=["", "dim"],
        )
        table.add_column("File", style="white")
        table.add_column("Language", style="cyan")
        table.add_column("Size (KB)", justify="right")
        table.add_column("Entry?", justify="center")
        table.add_column("Truncated?", justify="center")

        for f in result.files:
            table.add_row(
                f.path,
                f.language,
                str(f.size_kb),
                "✓" if f.is_entry_point else "",
                "⚠" if f.is_truncated else "",
            )

        console.print(table)

    #  Skip breakdown 
    if result.skipped_reasons and verbose:
        console.print("\n[dim]Skip reasons:[/dim]")
        for reason, count in sorted(result.skipped_reasons.items(), key=lambda x: -x[1]):
            console.print(f"  [dim]{reason}:[/dim] {count}")

    console.print(
        f"\n[green]✓[/green] Scan complete. "
        f"Run [bold cyan]readmegen generate {path}[/bold cyan] to produce a README.\n"
    )


#  generate command 

@cli.command()
def generate(
    path: Path = typer.Argument(
        default=".",
        help="Path to the repository to generate a README for.",
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o",
        help="Where to write the README. Defaults to <path>/README.md",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run",
        help="Print the README to terminal instead of writing it to disk.",
    ),
):
    """
    Generate a README for a repository (full pipeline).
    Phase 2 and 3 are coming soon — currently runs Phase 1 only.
    """
    root = path.resolve()
    if not root.exists() or not root.is_dir():
        console.print(f"[red]✗[/red] Invalid path: [bold]{root}[/bold]")
        raise typer.Exit(code=1)

    console.print()
    console.print(
        Panel(
            "[yellow]⚠[/yellow]  Phase 2 (AI analysis) and Phase 3 (README writing) "
            "are not built yet.\nRunning Phase 1 scan only for now.",
            border_style="yellow",
        )
    )
    console.print()

    with console.status("[bold cyan]Scanning repository...[/bold cyan]", spinner="dots"):
        result = run_generate(root)

    console.print(
        f"[green]✓[/green] Scanned [bold]{len(result.files)}[/bold] files from "
        f"[bold]{root.name}[/bold]. Analysis coming in Phase 2.\n"
    )


#  Entry point 

def main():
    cli()

if __name__ == "__main__":
    main()