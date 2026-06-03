# Co-ordinates the full pipeline across all the phases.

from pathlib import Path
from .scanner.walker import walk, WalkResult


def run_scan(root_path: Path) -> WalkResult:
    """
    Phase 1: scan the repo and returns the WalkResult
    called by the CLi "scan" command.
    """
    result = walk(root_path)
    return result

def run_generate(root_path: Path) -> None:

    # Phase 1: scan
    walk_result = run_scan(root_path)

    # Phase 2: analyse (stubbed)

    # Phase 3: generate README (stubbed)

    return walk_result