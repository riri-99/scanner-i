"""
    takes a reposnapshot and produces a token_budgeted string that the model can read and immediately understand the project.

"""

from __future__ import annotations
from pathlib import Path

from ..scanner.assembler import RepoSnapshot, FileSnapshot

# Token Budget
# Rough rule: 1 token ≈ 4 characters for English/code.
# We target 6,000 tokens → ~24,000 characters.
# Keeping headroom below the model's full context window
# ensures the prompt + system message + response all fit.

CHAR_BUDGET: int = 24_000

# Characters reserved for the metadata block (always included)
# Metadata is short so we hardcode an upper bound.

METADATA_RESERVE: int = 1_200

# Config file signatures

CONFIG_FILENAMES: set[str] = {
    "pyproject.toml", "setup.py", "setup.cfg",
    "package.json", "package-lock.json",
    "cargo.toml",
    "go.mod", "go.sum",
    "pom.xml", "build.gradle",
    "gemfile",
    "dockerfile", "docker-compose.yml", "docker-compose.yaml",
    ".env.example",
    "makefile",
    "procfile",
    ".github/workflows",
}

# Test file signals
TEST_SIGNALS: tuple[str, ...] = ("test", "spec", "_test.", "tests/", "__tests__/")

# public API

def build(snapshot: RepoSnapshot, char_budget: int = CHAR_BUDGET) -> str:
    
    # Build a trimmed context string from a RepoSnapshot
    sections: list[str] = []
    remaining = char_budget

    # 1. Metadata_block
    metadata = _build_metadata(snapshot)
    sections.append(metadata)
    remaining -= len(metadata)

    # Categorise files
    entry_files, config_files, source_files, test_files = _categorise(snapshot.files)

    # 2. Entry point files
    remaining = _add_files(
        files = entry_files,
        sections = sections,
        remaining = remaining,
        label = "entry point"
    )

    # Config files
    remaining = _add_files(
        files=config_files,
        sections=sections,
        remaining=remaining,
        label="config",
    )

    # 4. source files
    remaining = _add_files(
        files=source_files,
        sections=sections,
        remaining=remaining,
        label=None,   # no extra label — just the path
    )

    # 5. test files
    remaining = _add_files(
        files=test_files,
        sections=sections,
        remaining=remaining,
        label="test",
    )

    # join and return
    context = "\n\n".join(sections)
 
    return context


# Metadata builder

def _build_metadata(snapshot: RepoSnapshot) -> str:
    lines: list[str] = ["=== REPO METADATA ==="]

    
    lines.append(f"Name:             {snapshot.name}")
    lines.append(f"Primary language: {snapshot.primary_language}")
 
    if snapshot.languages:
        lines.append(f"All languages:    {', '.join(snapshot.languages)}")
 
    if snapshot.all_frameworks:
        lines.append(f"Frameworks:       {', '.join(snapshot.all_frameworks)}")
 
    # Production deps only — dev deps add noise without signal
    if snapshot.prod_deps:
        dep_names = [d.name for d in snapshot.prod_deps[:30]]  # cap at 30
        lines.append(f"Dependencies:     {', '.join(dep_names)}")
 
    if snapshot.entry_points:
        lines.append(f"Entry points:     {', '.join(snapshot.entry_points)}")
 
    # Ecosystem scripts (e.g. npm run dev, npm run build)
    for eco in snapshot.ecosystems:
        if eco.scripts:
            script_list = ", ".join(f"{k}: {v}" for k, v in list(eco.scripts.items())[:6])
            lines.append(f"Scripts ({eco.ecosystem}): {script_list}")
 
    # Convenience flags
    flags = []
    if snapshot.has_dockerfile: flags.append("Docker")
    if snapshot.has_tests:      flags.append("Tests")
    if snapshot.has_ci:         flags.append("CI/CD")
    if flags:
        lines.append(f"Detected:         {', '.join(flags)}")
 
    lines.append(f"File count:       {snapshot.file_count}")
 
    return "\n".join(lines)

# file categoriser

def _categorise(
    files: list[FileSnapshot],
) -> tuple[
    list[FileSnapshot],  # entry points
    list[FileSnapshot],  # config files
    list[FileSnapshot],  # regular source files
    list[FileSnapshot],  # test files
]:
    
    entry, config, source, tests = [], [], [], []
 
    for f in files:
        # Never include our own runtime output as context
        if f.path.startswith(".readmegen/"):
            continue
 
        path_lower = f.path.lower()
        name_lower = Path(f.path).name.lower()
 
        if f.is_entry_point:
            entry.append(f)
 
        elif _is_test_file(path_lower):
            tests.append(f)
 
        elif name_lower in CONFIG_FILENAMES or any(sig in path_lower for sig in CONFIG_FILENAMES):
            config.append(f)
 
        else:
            source.append(f)
 
    # Within each bucket, shorter paths first (top-level files before deeply nested ones)
    for bucket in (entry, config, source, tests):
        bucket.sort(key=lambda f: (f.path.count("/"), f.path))
 
    return entry, config, source, tests
 
 
def _is_test_file(path_lower: str) -> bool:
    return any(signal in path_lower for signal in TEST_SIGNALS)

# File adder
def _add_files(
    files: list[FileSnapshot],
    sections: list[str],
    remaining: int,
    label: str | None,
) -> int:
    
    for f in files:
        if remaining <= 0:
            break
 
        block = _format_file_block(f, label)

        if len(block) > remaining:
            block = block[:remaining].rstrip()
            block += "\n# ... [context limit reached] ..."
            sections.append(block)
            remaining = 0
            break
 
        sections.append(block)
        remaining -= len(block)
 
    return remaining
 
 
def _format_file_block(f: FileSnapshot, label: str | None) -> str:
    tag = f" ({label})" if label else ""
    header = f"=== FILE: {f.path}{tag} ==="
    truncation_note = "\n# ... [file truncated] ..." if f.is_truncated else ""
 
    return f"{header}\n{f.content}{truncation_note}"

# Diagnostic helper
def stats(snapshot: RepoSnapshot, char_budget: int = CHAR_BUDGET) -> dict:
    entry, config, source, tests = _categorise(snapshot.files)
    metadata_len = len(_build_metadata(snapshot))
 
    def total_chars(files: list[FileSnapshot]) -> int:
        return sum(len(f.content) + len(f.path) + 20 for f in files)
 
    return {
        "char_budget":    char_budget,
        "metadata_chars": metadata_len,
        "entry_files":    len(entry),
        "entry_chars":    total_chars(entry),
        "config_files":   len(config),
        "config_chars":   total_chars(config),
        "source_files":   len(source),
        "source_chars":   total_chars(source),
        "test_files":     len(tests),
        "test_chars":     total_chars(tests),
        "total_chars":    total_chars(entry + config + source + tests) + metadata_len,
        "fits_in_budget": (total_chars(entry + config + source + tests) + metadata_len) <= char_budget,
    }