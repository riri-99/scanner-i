# design reules and sections defined and applied throughout.

from __future__ import annotations

import re
import urllib.parse

from ..analyzer.parser import AnalysisObject
from ..scanner.assembler import RepoSnapshot


# Badge helpers

# License names to colors
_LICENSE_COLORS: dict[str, str] = {
    "mit": "blue",
    "apache": "orange",
    "gpl": "red",
    "bsd": "lightgrey",
    "isc": "green",
    "mozilla": "orange",
    "unlicense": "lightgrey",
}

# Language names to badge colors
_LANG_COLORS: dict[str, str] = {
    "python":     "3776ab",
    "javascript": "f7df1e",
    "typescript": "3178c6",
    "go":         "00add8",
    "rust":       "dea584",
    "java":       "b07219",
    "ruby":       "701516",
    "c#":         "178600",
    "php":        "4f5d95",
    "swift":      "f05138",
}

def _shield(label: str, message: str, color: str) -> str:

    label_enc = urllib.parse.quote(label, safe = "")
    message_enc = urllib.parse.quote(message, safe = "")
    url = f"https://img.shields.io/badge/{label_enc}-{message_enc}-{color}"
    return f"![{label}]({url})"

def _looks_like_command(text: str) -> bool:
    
    # used to decide whether to wrap setup steps in a bash code block or not?

    command_starters = (
        "pip ", "npm ", "yarn ", "pnpm ", "cargo ", "go ", "brew ",
        "apt ", "apt-get ", "docker ", "make ", "python", "node ",
        "git ", "curl ", "wget ", "cd ", "cp ", "mv ", "mkdir ",
        "uvicorn ", "gunicorn ", "flask ", "django", "./", "npx ",
        "bundle ", "gem ", "rake ", "mix ", "composer ", "php ",
    )

    stripped = text.strip().lower()
    return any(stripped.startswith(s) for s in command_starters)


# 1. Header

def render_header(snapshot: RepoSnapshot, analysis: AnalysisObject) -> str:
    raw_name = snapshot.name
    pretty_name = re.sub(r"[-_]", " ", raw_name).title()
    lines = [f"# {pretty_name}"]
    lines.append("")

    badges: list[str] = []

    lang = snapshot.primary_language.lower()
    if lang and lang != "unknown" and lang != "other":
        color = _LANG_COLORS.get(lang, "grey")
        badges.append(_shield("Language", snapshot.primary_language, color))

    if analysis.license:
        lic_lower = analysis.license.lower()
        color = next(
            (v for k, v in _LICENSE_COLORS.items() if k in lic_lower), "lightgrey"
        )

    if snapshot.has_dockerfile:
        badges.append(_shield("Docker", "ready", "2496ed"))

    if snapshot.has_ci:
        badges.append(_shield("CI", "configured", "4caf50"))

    if badges:
        lines.append("  ".join(badges))
 
    return "\n".join(lines)

# 2. About

def render_about(analysis: AnalysisObject) -> str:

    # Project's purpose
    if not analysis.purpose or not analysis.purpose.strip():
        return ""
    return f"## About\n\n{analysis.purpose.strip()}"

# 3. How It Works

def render_how_it_works(analysis: AnalysisObject) -> str:

    # Architecture overview
    if not analysis.how_it_works or not analysis.how_it_works.strip():
        return ""
    return f"## How It Works\n\n{analysis.how_it_works.strip()}"

# 4. Tech Stack

def render_tech_stack(analysis: AnalysisObject) -> str:

    # Bullet list of technologies
    items = [t.strip() for t in analysis.tech_stack if t.strip()]
    if not items:
        return ""
    bullets = "\n".join(f"- {item}" for item in items)
    return f"## Teck Stack\n\n{bullets}"

# 5. Prerequisites

def render_prerequisites(analysis: AnalysisObject) -> str:

    # what the user needs installed before the setip
    items = [p.strip() for p in analysis.prerequisites if p.strip()]
    if not items:
        return ""
    bullets = "\n".join(f"- {item}" for item in items)
    return f"## Prerequisites\n\n{bullets}"

# 6. Installations

def render_installation(analysis: AnalysisObject) -> str:

    # Ordered setup steps. Commands get their own bash code block. plain instructions stay as prose under the numbered item.
    steps = [s.strip() for s in analysis.setup_steps if s.strip()]
    if not steps:
        return ""
    
    lines = ["## Installation", ""]

    for i, step in enumerate(steps, 1):
        clean = re.sub(r"^\d+[\.\)]\s*", "", step).strip()

        if _looks_like_command(clean):
            lines.append(f"{i}. Run:")
            lines.append("")
            lines.append("  ```bash")
            lines.append("  {clean}")
            lines.append("  ```")
        else:
            lines.append(f"{i}. Run:")

        lines.append("")

    return "\n".join(lines).rstrip()

# 7. Usage

def render_usage(analysis: AnalysisObject) -> str:

    # usage exapmles as code block
    examples = [e.strip() for e in analysis.usage_examples if e.strip()]
    if not examples:
        return ""
    
    lines = ["## Usage", ""]

    for example in examples:
        lang = _infer_code_lang(example)
        lines.append(f"```{lang}")
        lines.append(example)
        lines.append("```")
        lines.append("")

    return "\n".join(lines).rstrip()

def _infer_code_lang(text: str) -> str:

    t = text.strip().lower()
    if t.startswith("curl") or t.startswith("http"):
        return "bash"
    if t.startswith("import ") or t.startswith("from ") or "def " in t:
        return "python"
    if t.startswith("const ") or t.startswith("let ") or "=>" in t:
        return "javascript"
    if t.startswith("open ") or t.startswith("https://") or t.startswith("http://"):
        return ""
    return "bash"

# 8. Environment VAriables

def render_env_variables(analysis: AnalysisObject) -> str:
    valid = [
        e for e in analysis.env_variables
        if isinstance(e, dict) and e.get("name", "").strip()
    ]
    if not valid:
        return ""
    
    lines = [
        "## Environment Variables",
        "",
        "| Variable | Description |",
        "|---|---|",
    ]

    for env in valid:
        name = env.get("name", "").strip()
        desc = env.get("description", "").strip()
        lines.append(f"| `{name}` | {desc} |")

    lines.append("")
    lines.append(
        "> Copy `.env.example` to `.env` and fill in the values before running."
        if _has_env_example(valid) else
        "> Create a `.env` file in the project root and set the variables above."
    )

    return "\n".join(lines)

def _has_env_example(env_vars: AnalysisObject) -> str:
    return len(env_vars) > 0

# 9. API references

def render_api_references(analysis: AnalysisObject) -> str:

    endpoints = [e.strip() for e in analysis.api_endpoints if e.strip()]
    if not endpoints:
        return ""
    
    lines = ["## API Reference", ""]

    for endpoint in endpoints:
        formatted = _format_endpoint(endpoint)
        lines.append(f"- {formatted}")

    return "\n".join(lines)

def _format_endpoint(raw: str) -> str:
    methods = ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "WS")

    for method in methods:
        if raw.upper().startswith(method + " ") and not raw.startswith("`"):
            parts = re.split(r"\s[—\-]\s", raw, maxsplit = 1)
            if len(parts) == 2:
                route, description = parts
                return f"`{route.strip()}` — {description.strip()}"
            else:
                return f"`{raw.strip()}`"
            
    return raw

# 10. Scripts

def render_scripts(analysis: AnalysisObject) -> str:
    scripts = {k.strip(): v.strip() for k,v in analysis.scripts.items() if k and v}
    if not scripts:
        return ""
    
    lines = [
        "## Scripts",
        "",
        "| Command | Description |",
        "|---|---|",
    ]

    for name, description in scripts.items():
        lines.append(f"| `{name}` | {description} |")

    return "\n".join(lines)

# 11. Contributing

def render_contributing(snapshot: RepoSnapshot) -> str:
    return (
        "## Contributing\n\n"
        "Pull requests are welcome. "
        "For major changes, please open an issue first to discuss what you would like to change."
    )

# 12. License

def render_license(analysis: AnalysisObject) -> str:
    if not analysis.license:
        return ""
    return f"## License\n\n[{analysis.license}](LICENSE)"

# Parse Warning

def render_parse_warning(analysis: AnalysisObject) -> str:
    if analysis.parse_success:
        return ""
    return (
        f"<!-- ⚠ README generated with partial analysis "
        f"(parse method: {analysis.parse_method}). "
        f"Review carefully before committing. -->"
    )

