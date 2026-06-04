# Co-ordinates the full pipeline across all the phases.

from pathlib import Path
from dataclasses import dataclass

from .scanner.walker import walk
from .scanner.parser import parse
from .scanner.assembler import assemble, save, load, RepoSnapshot


def run_scan(root_path: Path, use_cache: bool = False) -> RepoSnapshot:
    root_path = root_path.resolve()

    if use_cache:
        cached = load(root_path)
        if cached:
            return cached
        
    walk_result = walk(root_path)
    deps_result = parse(root_path)
    snapshot = assemble(walk_result, deps_result)
    save(snapshot, root_path)
    return snapshot



def run_generate(root_path: Path) -> RepoSnapshot:
    snapshot = run_scan(root_path)
    return snapshot
