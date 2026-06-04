from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import json

from pydantic import BaseModel, Field

from .walker import WalkResult, FileEntry as WalkedFile
from .parser import AllDependencies

# pydantic models for the output of the assembler phase

class FileSnapshot(BaseModel):
    path: str
    language: str
    size_kb: float
    content: str
    is_truncated: bool
    is_entry_point: bool

class DependencySnapshot(BaseModel):
    name: str
    version: str = ""
    is_dev: bool = False

class EcosystemSnapshot(BaseModel):
    ecosystem: str
    source_file: str
    dependencies: list[DependencySnapshot]
    frameworks: list[str]
    scripts: dict[str, str] = Field(default_factory=dict)

class RepoSnapshot(BaseModel):

    # Identity
    name: str
    root: str
    scanned_at: str

    # Files
    primary_language: str
    languages: list[str]
    entry_points: list[str]
    files: list[FileSnapshot]
    file_count: int
    skipped_count: int
    
    # Dependencies
    ecosystems: list[EcosystemSnapshot]
    all_frameworks: list[str]
    prod_deps: list[DependencySnapshot]
    dev_deps: list[DependencySnapshot]

    # Convenience flags
    has_dockerfile: bool
    has_tests: bool
    has_ci: bool


# Assembler

def assemble(walk: WalkResult, deps: AllDependencies) -> RepoSnapshot:
    
    from collections import Counter

    root_path = Path(walk.root)

    # Language Stats
    lang_counts = Counter(f.language for f in walk.files if f.language != "Other")
    languages = [lang for lang, _ in lang_counts.most_common()]
    primary_lang = languages[0] if languages else "Unknown"

    # Entry Points
    entry_points = [f.path for f in walk.files if f.is_entry_point]

    # File snapshots
    file_snapshots = [
        FileSnapshot(
            path = f.path,
            language = f.language,
            size_kb = f.size_kb,
            content = f.content,
            is_truncated = f.is_truncated,
            is_entry_point = f.is_entry_point,
        )
        for f in walk.files
    ]

    # Ecosystem snapshots
    ecosystem_snapshots = [
        EcosystemSnapshot(
            ecosystem=r.ecosystem,
            source_file=r.source_file,
            dependencies=[
                DependencySnapshot(name=d.name, version=d.version, is_dev=d.is_dev)
                for d in r.dependencies
            ],
            frameworks=r.frameworks,
            scripts=r.raw_scripts,
        )
        for r in deps.results
    ]

    all_deps = deps.all_dependencies
    prod_deps = [
        DependencySnapshot(name=d.name, version=d.version)
        for d in all_deps if not d.is_dev
    ]
    dev_deps = [
        DependencySnapshot(name=d.name, version=d.version, is_dev=True)
        for d in all_deps if d.is_dev
    ]

    # Convenience flags
    all_paths     = {f.path.lower() for f in walk.files}
    all_filenames = {Path(f.path).name.lower() for f in walk.files}
 
    has_dockerfile = any(
        name in all_filenames for name in ("dockerfile", "docker-compose.yml", "docker-compose.yaml")
    )
    has_tests = any(
        part in all_paths
        for f_path in all_paths
        for part in [f_path]
        if "test" in f_path or "spec" in f_path
    )
    has_ci = any(
        ".github/workflows" in p or ".gitlab-ci" in p or "jenkinsfile" in p.lower()
        or "circleci" in p
        for p in all_paths
    )
 
    return RepoSnapshot(
        name=root_path.name,
        root=str(root_path),
        scanned_at=datetime.now(timezone.utc).isoformat(),
        primary_language=primary_lang,
        languages=languages,
        entry_points=entry_points,
        files=file_snapshots,
        file_count=len(walk.files),
        skipped_count=walk.skipped_count,
        ecosystems=ecosystem_snapshots,
        all_frameworks=deps.all_frameworks,
        prod_deps=prod_deps,
        dev_deps=dev_deps,
        has_dockerfile=has_dockerfile,
        has_tests=has_tests,
        has_ci=has_ci,
    )

# Persistence

SNAPSHOT_DIR = ".readmegen"
SNAPSHOT_FILE = "snapshot.json"

def save(snapshot: RepoSnapshot, root: Path) -> Path:

    out_dir = root / SNAPSHOT_DIR
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / SNAPSHOT_FILE

    out_path.write_text(
        snapshot.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return out_path

def load(root: Path) -> RepoSnapshot | None:
    snap_path = root / SNAPSHOT_DIR / SNAPSHOT_FILE
    if not snap_path.exists():
        return None
 
    return RepoSnapshot.model_validate_json(snap_path.read_text(encoding="utf-8"))

