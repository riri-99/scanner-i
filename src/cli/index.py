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
    path: Path = typer.Argument(
        default=".",
        help="Path to the repository to scan.",
        show_default=True,
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v",
        help="Show every collected file and all skip reasons.",
    ),
):
    """
    Scan a repository and display what was found.
    Runs Phase 1 only — no README is generated yet.
    """
    # ── Validate path ─────────────────────────────────────────────────────────
    root = path.resolve()
    if not root.exists():
        console.print(f"[red]✗[/red] Path does not exist: [bold]{root}[/bold]")
        raise typer.Exit(code=1)
    if not root.is_dir():
        console.print(f"[red]✗[/red] Not a directory: [bold]{root}[/bold]")
        raise typer.Exit(code=1)

    # ── Run Phase 1 ───────────────────────────────────────────────────────────
    console.print()
    with console.status(
        f"[bold cyan]Scanning[/bold cyan] [dim]{root}[/dim]...",
        spinner="dots",
    ):
        result = run_scan(root)

    walk = result.walk
    deps = result.deps

    # ── Derived values ────────────────────────────────────────────────────────
    lang_counts  = Counter(f.language for f in walk.files)
    top_langs    = ", ".join(
        f"{lang} ([green]{count}[/green])" for lang, count in lang_counts.most_common(5)
    )
    entry_points = [f.path for f in walk.files if f.is_entry_point]
    truncated    = sum(1 for f in walk.files if f.is_truncated)
    all_frameworks = deps.all_frameworks
    all_deps       = [d for d in deps.all_dependencies if not d.is_dev]
    dev_deps       = [d for d in deps.all_dependencies if d.is_dev]
    ecosystems     = deps.ecosystems

    # ── Summary panel ─────────────────────────────────────────────────────────
    summary = Text()

    summary.append("  Repo:           ", style="dim")
    summary.append(f"{root.name}\n", style="bold white")

    summary.append("  Files found:    ", style="dim")
    summary.append(f"{len(walk.files)}", style="bold green")
    summary.append(f"  (skipped {walk.skipped_count})\n", style="dim")

    summary.append("  Languages:      ", style="dim")
    summary.append(Text.from_markup(f"{top_langs or 'none detected'}\n"))

    summary.append("  Entry points:   ", style="dim")
    summary.append(
        f"{', '.join(entry_points) or 'none detected'}\n",
        style="magenta",
    )

    summary.append("  Ecosystems:     ", style="dim")
    summary.append(
        f"{', '.join(ecosystems) if ecosystems else 'none detected'}\n",
        style="cyan",
    )

    summary.append("  Frameworks:     ", style="dim")
    summary.append(
        f"{', '.join(all_frameworks) if all_frameworks else 'none detected'}\n",
        style="bold cyan",
    )

    summary.append("  Dependencies:   ", style="dim")
    summary.append(f"{len(all_deps)} prod", style="green")
    if dev_deps:
        summary.append(f"  {len(dev_deps)} dev", style="dim")
    summary.append("\n")

    if truncated:
        summary.append("  Truncated:      ", style="dim")
        summary.append(f"{truncated} files (content too large)\n", style="yellow")

    console.print(Panel(summary, title="[bold]Scan Results[/bold]", border_style="cyan"))

    # ── Dependency breakdown (always shown, not just verbose) ─────────────────
    if deps.results:
        for parse_result in deps.results:
            prod = [d for d in parse_result.dependencies if not d.is_dev]
            dev  = [d for d in parse_result.dependencies if d.is_dev]
            label = f"[bold]{parse_result.ecosystem}[/bold] [dim]({parse_result.source_file})[/dim]"

            dep_table = Table(box=box.SIMPLE, show_header=True, header_style="dim")
            dep_table.add_column("Package", style="white")
            dep_table.add_column("Version", style="dim")
            dep_table.add_column("Type", style="dim")

            for d in prod[:20]:   # cap display at 20 prod deps
                dep_table.add_row(d.name, d.version or "—", "prod")
            for d in dev[:5]:     # show up to 5 dev deps
                dep_table.add_row(d.name, d.version or "—", "[dim]dev[/dim]")

            if len(prod) > 20:
                dep_table.add_row(f"[dim]... and {len(prod) - 20} more[/dim]", "", "")

            console.print(f"\n  {label}")
            console.print(dep_table)

        if all_frameworks:
            console.print(
                f"\n  [dim]Detected frameworks →[/dim] "
                + "  ".join(f"[bold cyan]{f}[/bold cyan]" for f in all_frameworks)
            )

    # ── Verbose: full file table ───────────────────────────────────────────────
    if verbose:
        console.print()
        table = Table(
            box=box.SIMPLE_HEAD,
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("File", style="white")
        table.add_column("Language", style="cyan")
        table.add_column("Size (KB)", justify="right")
        table.add_column("Entry?", justify="center")
        table.add_column("Truncated?", justify="center")

        for f in walk.files:
            table.add_row(
                f.path,
                f.language,
                str(f.size_kb),
                "[green]✓[/green]" if f.is_entry_point else "",
                "[yellow]⚠[/yellow]"  if f.is_truncated  else "",
            )
        console.print(table)

        if walk.skipped_reasons:
            console.print("\n[dim]Skip reasons:[/dim]")
            for reason, count in sorted(walk.skipped_reasons.items(), key=lambda x: -x[1]):
                console.print(f"  [dim]{reason}:[/dim] {count}")

    console.print(
        f"\n[green]✓[/green] Phase 1 complete. "
        f"Run [bold cyan]readmegen generate {path}[/bold cyan] to produce a README.\n"
    )


# ── generate command ──────────────────────────────────────────────────────────

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
        help="Print the README to terminal instead of writing a file.",
    ),
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
        result = run_generate(root)

    console.print(
        f"[green]✓[/green] Scanned [bold]{len(result.walk.files)}[/bold] files  "
        f"[bold]{len(result.deps.all_frameworks)}[/bold] frameworks detected  "
        f"[bold]{len(result.deps.all_dependencies)}[/bold] dependencies found\n"
        f"Analysis coming in Phase 2.\n"
    )


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    cli()

if __name__ == "__main__":
    main()