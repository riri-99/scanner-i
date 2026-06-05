"""
Prompt Builder

2 design principle here:
    1. JSON schema in the prompt — the model fills in the schema like a form rather than free writing.
    2. Strict output contract in the system prompt - gives raw json only.

"""

from __future__ import annotations

from ..scanner.assembler import RepoSnapshot

# Output schema
# written as a json-like string rather than a python dict so it reads naturally inside the prompt and the model sees exactly what format is expected.

_SCHEMA = """{
    "purpose": "One clear sentence: what does this project do and who is it for?",
    "how_it_works": "2-3 sentences describing the architecture and main approach",
    "tech_stack": [
            "Primary language and version if detectable",
            "Frameworks and major libraries",
            "Database or storage layer if present",
            "Infrastructure tools (Docker, CI etc) if prresent"
    ],
    "prerequisites": [
            "What the user needs installed before they can run this project",
            "e.g. Pythpon 3.11+, Node.js 18+, Docker, Go 1.21+"
    ],
    "setup_steps": [
            "1. Exact command or instruction",
            "2. Next step",
            "3. Continue in order until the project is running"
    ],
    "usage_examples": [
            " A realistic command or code snippet showing the main use case",
            "A second exapmle if the project has multiple entry points"
    ],
    "env_variables": [
            {"name": "VAR_NAME", "description": "what this variable controls and where to get the value"}
    ],
    "api_endpoint": ["METHOD /path - what it does and what it returns"],
    "scripts": {"script_name": "plain English description of hwat running htis script does"},
    "license": "License name as a string, or null if not detected"
}"""


# System prompt

_SYSTEM_PROMPT = """\
You are a senior software engineer writing technical documentation for a \
public GitHub repository.
 
Your task: analyze the repository context provided and extract structured \
information that will be used to generate a README file.
 
Output rules (follow exactly):
- Return ONLY a valid JSON object — no preamble, no explanation, no commentary
- Do NOT wrap the JSON in markdown fences (no ```json or ```)
- Every field in the schema must be present, even if empty (use [] or null)
- If a field cannot be determined from the context, use an empty list [] or null
- For setup_steps: write real, runnable commands — not vague instructions
- For api_endpoints: only include endpoints you can actually see in the code
- Be concise and precise — this output feeds directly into documentation\
"""

# User prompt template

_USER_TEMPLATE = """\
Analyze this repository and return a JSON object matching this exact schema:
 
{schema}
 
Important notes:
- setup_steps should be a numbered, ordered sequence of actual commands
- tech_stack should list concrete names (e.g. "FastAPI 0.100", not just "web framework")
- prerequisites should be user-facing requirements, not dev dependencies
- if env_variables is empty (no .env.example and no os.environ usage visible), return []
- if api_endpoints is empty (not an API project), return []
- scripts should come from the package.json scripts block or Makefile targets if visible
 
=== REPOSITORY CONTEXT ===
{context}\
"""


# Public API

def build(context: str) -> tuple[str, str]:
    user_prompt = _USER_TEMPLATE.format(
        schema = _SCHEMA,
        context = context,
    )
    return _SYSTEM_PROMPT, user_prompt

def build_from_snapshot(snapshot: RepoSnapshot) -> tuple[str, str]:
    from .context import build as build_context
    context = build_context(snapshot)
    return build(context)

# Diagnostic helpers

def char_counts(context: str) -> dict:
    """
    Rough budget guide:
      codellama:7b  → 4,096 token context window  (~16,000 chars total)
      mistral:7b    → 8,192 token context window  (~32,000 chars total)
      llama3.2:3b   → 8,192 token context window  (~32,000 chars total)
      groq llama3   → 8,192 token context window  (~32,000 chars total)

    """
    system, user = build(context)
    total = len(system) + len(user)
    return{
        "system_chars":      len(system),
        "system_tokens_est": len(system) // 4,
        "user_chars":        len(user),
        "user_tokens_est":   len(user) // 4,
        "total_chars":       total,
        "total_tokens_est":  total // 4,
        "fits_codellama_7b": (total // 4) < 3_500,
        "fits_mistral_7b":   (total // 4) < 7_500,
    }
