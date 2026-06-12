"""
Checks through a repo and collects every file worth reading.
and rerturns a list of FileEntry objects

"""

from pathlib import Path
from dataclasses import dataclass, field
import json

from .filter import FileFilter

# Load Config file

from ..utils.config import get as _get_config
_CFG = _get_config("scanner")


MAX_FILE_SIZE_KB: int = _CFG["max_file_size_kb"]
MAX_FILES: int = _CFG["max_files"]
MAX_CONTENT_CHARS: int = _CFG["max_file_content_chars"]
MAX_ENTRY_POINT_CHARS: int = _CFG.get("max_entry_point_chars", MAX_CONTENT_CHARS)


# Known entry point filenames to prioritize
ENTRY_POINT_NAMES: set[str] = {
    # Python
    "main.py", "app.py", "server.py", "run.py", "manage.py", "wsgi.py", "asgi.py",
    # JavaScript / TypeScript
    "index.js", "main.js", "app.js", "server.js",
    "index.ts", "main.ts", "app.ts", "server.ts",
    "index.jsx", "main.jsx", "index.tsx", "main.tsx",
    # Go
    "main.go",
    # Rust
    "main.rs",
    # Java
    "Main.java", "Application.java",
    # Ruby
    "app.rb", "main.rb", "server.rb",
    # C / C++
    "main.c", "main.cpp",
    # Generic
    "index.php", "index.html",
}


# Data Model
@dataclass
class FileEntry:
    """Represents one file collected from the repository."""
    path: str               # relative path from repo root  e.g. "src/main.py"
    abs_path: str           # absolute path on disk
    language: str           # derived from extension        e.g. "Python"
    size_kb: float          # file size in kilobytes
    content: str            # raw text content (truncated if needed)
    is_truncated: bool      # True if content was cut short
    is_entry_point: bool    # True if this looks like a program entry point
 
 
@dataclass
class WalkResult:
    """Everything the walker collected from one scan."""
    root: str               # absolute path of the scanned directory
    files: list[FileEntry] = field(default_factory=list)
    skipped_count: int = 0  # files that were filtered out
    skipped_reasons: dict[str, int] = field(default_factory=dict)  # reason → count
 

 # Extension to language mapping (simplified)
EXTENSION_TO_LANGUAGE: dict[str, str] = {
    ".py":    "Python",
    ".js":    "JavaScript",
    ".ts":    "TypeScript",
    ".jsx":   "JavaScript",
    ".tsx":   "TypeScript",
    ".go":    "Go",
    ".rs":    "Rust",
    ".java":  "Java",
    ".kt":    "Kotlin",
    ".rb":    "Ruby",
    ".php":   "PHP",
    ".cs":    "C#",
    ".cpp":   "C++",
    ".c":     "C",
    ".h":     "C/C++",
    ".swift": "Swift",
    ".sh":    "Shell",
    ".bash":  "Shell",
    ".zsh":   "Shell",
    ".yaml":  "YAML",
    ".yml":   "YAML",
    ".json":  "JSON",
    ".toml":  "TOML",
    ".md":    "Markdown",
    ".html":  "HTML",
    ".css":   "CSS",
    ".scss":  "SCSS",
    ".sql":   "SQL",
    ".tf":    "Terraform",
    ".dockerfile": "Docker",
}


# Main Walker Logic

def walk(root_path: Path) -> WalkResult:
    result = WalkResult(root=str(root_path.resolve()))
    file_filter = FileFilter(root_path)

    all_paths = [p for p in root_path.rglob("*") if p.is_file()]

    for path in sorted(all_paths):

        # Filter check
        ignored, reason = file_filter.should_ignore(path)
        if ignored:
            result.skipped_count += 1
            result.skipped_reasons[reason] = result.skipped_reasons.get(reason, 0) + 1
            continue

        # Size check
        size_kb = path.stat().st_size / 1024
        if size_kb > MAX_FILE_SIZE_KB:
            result.skipped_count += 1
            result.skipped_reasons["too large"] = result.skipped_reasons.get("too large", 0) + 1
            continue

        # Determine if it is an entry point before reading
        is_entry_point = path.name in ENTRY_POINT_NAMES
        limit = MAX_ENTRY_POINT_CHARS if is_entry_point else MAX_CONTENT_CHARS

        # Read content
        content, is_truncated = _read_file(path, limit)
        if content is None:
            result.skipped_count += 1
            result.skipped_reasons["binary/unreadable"] = result.skipped_reasons.get("binary/unreadable", 0) + 1
            continue

        # Build FileEntry
        relative_path = str(path.relative_to(root_path))
        entry = FileEntry(
            path = str(relative_path),
            abs_path = str(path.resolve()),
            language = _detect_language(path),
            size_kb = round(size_kb, 2),
            content = content,
            is_truncated = is_truncated,
            is_entry_point = is_entry_point,
        )     
        result.files.append(entry)

    result.files.sort(key = lambda f: (not f.is_entry_point, f.path))  # entry points first, then alphabetically

    return result

# HELPERS
def _read_file(path: Path, max_chars: int) -> tuple[str | None, bool]:

    # reads a file's content safely, returns (content, is_truncated)
    try:
        raw = path.read_text(encoding="utf-8", errors="strict")
    except (UnicodeDecodeError, PermissionError):
        return None, False
    
    if len(raw) > max_chars:
        truncated = raw[:max_chars]
        last_newline = truncated.rfind("\n")
        if last_newline > max_chars * 0.8:
            truncated = truncated[:last_newline]
        return truncated + "\n... [truncated] ...", True
    
    return raw, False

def _detect_language(path: Path) -> str:

    # returns a human-friendly language name based on the file extension, or "Unknown"
    name_map = {
        "Dockerfile": "Dockerfile",
        "Makefile": "Makefile",
        "Procfile": "Procfile",
        ".env.example": "Config"
    }

    if path.name in name_map:
        return name_map[path.name]
    
    return EXTENSION_TO_LANGUAGE.get(path.suffix.lower(), "Unknown")