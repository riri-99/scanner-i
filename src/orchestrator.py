# Co-ordinates the full pipeline across all the phases.

from pathlib import Path
from dataclasses import dataclass

from .scanner.walker import walk, WalkResult
from .scanner.parser import parse, AllDependencies

@dataclass
class ScanResult:
    walk: WalkResult
    deps: AllDependencies


# PAHSE 1
def run_scan(root_path: Path) -> WalkResult:
    """
    Phase 1: scan the repo and returns the WalkResult
    called by the CLi "scan" command.
    """
    walk_result = walk(root_path)
    deps_result = parse(root_path)
    return ScanResult(walk=walk_result, deps=deps_result)

def run_generate(root_path: Path) -> None:

    # Phase 1: scan
    scan_result = run_scan(root_path)

    # Phase 2: analyse (stubbed)

    # Phase 3: generate README (stubbed)

    return scan_result