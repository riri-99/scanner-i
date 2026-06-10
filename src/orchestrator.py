# coordinates the full pipeline

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .scanner.walker import walk
from .scanner.parser import parse as parse_deps
from .scanner.assembler import assemble, save as save_snapshot, load as load_snapshot, RepoSnapshot
from .analyzer.context import build as build_context
from .analyzer.prompts import build as build_prompts
from .analyzer.router import get_client
from .analyzer.parser import parse as parse_response, AnalysisObject
from .writer.writer import write as write_readme, WriteResult


# Paths

READMEGEN_DIR = ".readmegen"
ANALYSIS_FILE = "analysis.json"


# Full Pipeline result

@dataclass
class GenerateResult:
    snapshot: RepoSnapshot
    analysis: AnalysisObject
    write_result: WriteResult


# Phase 1

def run_scan(root_path: Path, use_cache: bool = False) -> RepoSnapshot:

    root_path = root_path.resolve()

    if use_cache:
        cached = load_snapshot(root_path)
        if cached:
            return cached
        
    walk_result = walk(root_path)
    deps_result = parse_deps(root_path)
    snapshot = assemble(walk_result, deps_result)
    save_snapshot(snapshot, root_path)

    return snapshot


# Phase 2

def run_analyze(
        snapshot: RepoSnapshot,
        root_path: Path,
        use_cache: bool = False,
        template: str = "standard",
) -> AnalysisObject:
    
    root_path = root_path.resolve()

    if use_cache:
        cached = load_analysis(root_path)
        if cached:
            return cached
    
    # 1. build context and prompts
    context_str = build_context(snapshot)
    system, user = build_prompts(context_str, template=template)

    # 2. pick backend
    client = get_client()

    # 3. call the model
    raw_response = client.complete(system, user)
    
    # 4. parse response into AnalysisObject
    analysis = parse_response(raw_response)

    # 5. save to .json file
    save_analysis(analysis, root_path)

    return analysis


# Phase 3 stub

def run_write(
    analysis:  AnalysisObject,
    snapshot:  RepoSnapshot,
    root_path: Path,
    output:    Path | None = None,
    template:  str         = "standard",
    dry_run:   bool        = False,
) -> WriteResult:
    
    return write_readme(
        analysis = analysis,
        snapshot = snapshot,
        root     = root_path.resolve(),
        output   = output,
        template = template,
        dry_run  = dry_run,
    )


# Full Pipeline

def run_generate(
    root_path: Path,
    output:    Path | None = None,
    template:  str         = "standard",
    dry_run:   bool        = False,
    use_cache: bool        = False,
) -> GenerateResult:

    root_path = root_path.resolve()
 
    snapshot     = run_scan(root_path, use_cache=use_cache)
    analysis     = run_analyze(snapshot, root_path, use_cache=use_cache)
    write_result = run_write(
        analysis  = analysis,
        snapshot  = snapshot,
        root_path = root_path,
        output    = output,
        template  = template,
        dry_run   = dry_run,
    )
 
    return GenerateResult(
        snapshot     = snapshot,
        analysis     = analysis,
        write_result = write_result,
    )


# save_analysis and load_analysis calls

def save_analysis(analysis: AnalysisObject, root: Path) -> Path:
    out_dir = root / READMEGEN_DIR
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / ANALYSIS_FILE
    out_path.write_text(
        analysis.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return out_path

def load_analysis(root: Path) -> AnalysisObject | None:
    path = root / READMEGEN_DIR / ANALYSIS_FILE
    if not path.exists():
        return None
    return AnalysisObject.model_validate_json(path.read_text(encoding="utf-8"))

