# file writer, basically takes a rendered markdown string andwrites it to disk safely.

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule

from ..analyzer.parser import AnalysisObject
from ..scanner.assembler import RepoSnapshot
from .template import render as render_template

# Constants

DEFAULT_OUTPUT_NAME = "README.md"
BACKUP_SUBDIR = ".readmegen"
BACKUP_FILENAME = "README.md.bak"

console = Console()


# Result dataclass

@dataclass
class WriteResult:
    output_path: Path
    backup_path: Path
    was_dry_run: bool
    line_count: int
    char_count: int
    had_existing: bool


# Public API

def write(
        analysis: AnalysisObject,
        snapshot: RepoSnapshot,
        root: Path,
        output: Path | None = None,
        template: str = "standard",
        dry_run: bool = False,
) -> WriteResult:
    
    # Reender markdown
    markdown_str = render_template(analysis, snapshot, template=template)

    # resolve output path
    output_path = (output or (root / DEFAULT_OUTPUT_NAME)).resolve()

    # dry run - print nd return
    if dry_run:
        return _dry_run(markdown_str, output_path, analysis)
    
    # check for existing Readme
    backup_path = None
    had_existing = output_path.exists()

    if had_existing:
        backup_path = _backup(output_path, root)

    # write to disk
    output_path.parent.mkdir(parents = True, exist_ok=True)
    output_path.write_text(markdown_str, encoding="utf-8")

    return WriteResult(
        output_path = output_path,
        backup_path= backup_path,
        was_dry_run= False,
        line_count= markdown_str.count("\n"),
        char_count= len(markdown_str),
        had_existing= had_existing,
    )


# DRY RUN

def _dry_run(markdown_str: str, output_path: Path, analysis: AnalysisObject) -> WriteResult:
    
    console.print()
    console.print(Rule(f"[bold]README preview[/bold] [dim](dry run - not written to disk)[/dim]"))
    console.print()

    console.print(Markdown(markdown_str))

    console.print()
    console.print(Rule("[dim]end of preview[/dim]"))

    if not analysis.parse_success:
        console.print(
            f"\n[yellow]⚠[/yellow]  Partial analysis "
            f"[dim](method: {analysis.parse_method})[/dim] — "
            f"review sections marked incomplete before committing."
        )

    console.print(
        f"\n[dim]Would write to:[/dim] [bold]{output_path}[/bold]  "
        f"[dim]({markdown_str.count(chr(10))} lines, {len(markdown_str)} chars)[/dim]\n"
        f"Remove [bold cyan]--dry-run[/bold cyan] to write the file."
    )

    return WriteResult(
        output_path= output_path,
        backup_path= None,
        was_dry_run= True,
        line_count= markdown_str.count("\n"),
        char_count= len(markdown_str),
        had_existing= output_path.exists(),
    )


# BAckup

def _backup(existing_path: Path, root: Path) -> Path:
    backup_dir = root / BACKUP_SUBDIR
    backup_dir.mkdir(exist_ok= True)
    backup_path = backup_dir / BACKUP_FILENAME

    shutil.copy2(existing_path, backup_path)
    return backup_path


