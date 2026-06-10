# Calls each section renderer, collects the results into a context dict, then renders a Jinja2 template with that context. Empty sections are set to "" so the template can skip them cleanly.

from __future__ import annotations

import re
from pathlib import Path

from jinja2 import Environment, BaseLoader, StrictUndefined, Undefined

from ..analyzer.parser import AnalysisObject
from ..scanner.assembler import RepoSnapshot
from . import sections as sec

# Buil in template directory

_TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"
BUILTIN_TEMPLATES = ("minimal", "standard", "professional", "detailed")


# Public API

def render(
        analysis: AnalysisObject,
        snapshot: RepoSnapshot,
        template: str = "standard",
) -> str:
    
    # Build section context
    ctx = _build_context(analysis, snapshot)

    # Load template score
    template_src = _load_template(template)

    # Render via jinja2
    rendered = _render_jinja(template_src, ctx)

    # Clean up
    cleaned = _clean_whitespace(rendered)

    return cleaned


# Context builder

def _build_context(analysis: AnalysisObject, snapshot: RepoSnapshot) -> dict:

    return {
        # Rendered sections (Markdown strings) 
        "header":        sec.render_header(snapshot, analysis),
        "about":         sec.render_about(analysis),
        "how_it_works":  sec.render_how_it_works(analysis),
        "tech_stack":    sec.render_tech_stack(analysis),
        "prerequisites": sec.render_prerequisites(analysis),
        "installation":  sec.render_installation(analysis),
        "usage":         sec.render_usage(analysis),
        "env_variables": sec.render_env_variables(analysis),
        "api_reference": sec.render_api_reference(analysis),
        "scripts":       sec.render_scripts(analysis),
        "contributing":  sec.render_contributing(snapshot),
        "license":       sec.render_license(analysis),
        "parse_warning": sec.render_parse_warning(analysis),
 
        # Raw fields for custom templates 
        "name":             snapshot.name,
        "purpose":          analysis.purpose,
        "how_it_works_raw": analysis.how_it_works,
        "tech_stack_list":  analysis.tech_stack,
        "prerequisites_list": analysis.prerequisites,
        "setup_steps":      analysis.setup_steps,
        "usage_examples":   analysis.usage_examples,
        "env_vars":         analysis.env_variables,
        "endpoints":        analysis.api_endpoints,
        "scripts_dict":     analysis.scripts,
        "license_name":     analysis.license or "",
        "primary_language": snapshot.primary_language,
        "frameworks":       snapshot.all_frameworks,
        "has_docker":       snapshot.has_dockerfile,
        "has_tests":        snapshot.has_tests,
        "has_ci":           snapshot.has_ci,
        "parse_success":    analysis.parse_success,
    }


# Template loader

def _load_template(template: str) -> str:

    if template in BUILTIN_TEMPLATES:
        template_path = _TEMPLATES_DIR / f"{template}.md"
        if not template_path.exists():
            raise FileNotFoundError(
                f"Built-in template '{template}' not found at {template_path}. "
                    f"Re-install the package to restore it."
            )

        return template_path.read_text(encoding="utf-8")
    
    # Custom file path
    custom_path = Path(template)
    if not custom_path.exists():
        raise FileNotFoundError(
            f"Custom template not found: {custom_path}\n"
            f"Built-in options: {', '.join(BUILTIN_TEMPLATES)}"
        )
    
    if custom_path.suffix not in (".md", ".txt", ".j2"):
        raise ValueError(
            f"Template must be a .md, .txt, .j2 file - got: {custom_path.suffix}"
        )
    
    return custom_path.read_text(encoding="utf-8")

# Jinja2 rendering

def _render_jinja(template_src: str, ctx: dict) -> str:

    env = Environment(
        loader=BaseLoader(),
        undefined=Undefined,         
        keep_trailing_newline=True,
        trim_blocks=True,            
        lstrip_blocks=True,
    )
    tmpl = env.from_string(template_src)
    return tmpl.render(**ctx)


# Post processing

def _clean_whitespace(text: str) ->str:

    text = text.replace("\r\n", "\n").replace("\r", "\n")

    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip() + "\n"


# Diagnostic helper

def available_variables() -> dict[str, str]:

    return{
        "{{ header }}":           "Project title + badge row",
        "{{ about }}":            "Purpose paragraph (## About section)",
        "{{ how_it_works }}":     "Architecture overview (## How It Works section)",
        "{{ tech_stack }}":       "Tech stack bullet list",
        "{{ prerequisites }}":    "Prerequisites bullet list",
        "{{ installation }}":     "Numbered installation steps",
        "{{ usage }}":            "Usage examples in code blocks",
        "{{ env_variables }}":    "Environment variables table",
        "{{ api_reference }}":    "API endpoints list",
        "{{ scripts }}":          "Scripts table",
        "{{ contributing }}":     "Contributing boilerplate",
        "{{ license }}":          "License line",
        "{{ parse_warning }}":    "HTML comment if analysis was partial",
        "{{ name }}":             "Repository name (raw)",
        "{{ purpose }}":          "Purpose string (raw, no heading)",
        "{{ setup_steps }}":      "List of setup step strings",
        "{{ tech_stack_list }}":  "List of tech stack strings",
        "{{ env_vars }}":         "List of {name, description} dicts",
        "{{ endpoints }}":        "List of API endpoint strings",
        "{{ scripts_dict }}":     "Dict of script name → description",
        "{{ license_name }}":     "License name string",
        "{{ primary_language }}": "Primary detected language",
        "{{ frameworks }}":       "List of detected framework names",
        "{{ has_docker }}":       "True if Dockerfile detected",
        "{{ has_tests }}":        "True if test files detected",
        "{{ has_ci }}":           "True if CI config detected",
        "{{ parse_success }}":    "True if model output parsed cleanly",
    }
