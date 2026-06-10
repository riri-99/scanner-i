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
  "how_it_works": "2-3 sentences describing the architecture and how the main components fit together.",
  "tech_stack": [
    "List every technology with its version if detectable e.g. Python 3.11, FastAPI 0.100, PostgreSQL 15"
  ],
  "prerequisites": [
    "Exact software the user must install before setup e.g. Python 3.11+, Node.js 18+, Docker, PostgreSQL"
  ],
  "setup_steps": [
    "IMPORTANT: every step must be a real, runnable shell command. NO prose instructions.",
    "e.g. git clone https://github.com/owner/repo",
    "e.g. cd repo",
    "e.g. pip install -r requirements.txt",
    "e.g. cp .env.example .env",
    "e.g. uvicorn main:app --reload"
  ],
  "usage_examples": [
    {
      "explanation": "A short sentence explaining what this example demonstrates or how the command works",
      "example": "A realistic, runnable command or code snippet showing the primary use case"
    }
  ],
  "env_variables": [
    {"name": "VARIABLE_NAME", "description": "What this controls and where to get the value e.g. get from https://console.groq.com"}
  ],
  "api_endpoints": [
    "METHOD /path — what it does and what it returns (only include endpoints visible in the code)"
  ],
  "scripts": {
    "script_name": "plain English description of what this script does when run"
  },
  "license": "Exact license name as a string e.g. MIT, Apache-2.0, or null if not found"
}"""


# System prompt

_SYSTEM = """\
You are a senior software engineer writing technical documentation for a public GitHub repository.
 
Analyze the repository context and extract structured information for a README file.
 
Critical output rules — follow exactly:
- Return ONLY a raw JSON object. No preamble, no explanation, no markdown fences (no ```json).
- Every field must be present. Use [] for empty lists and null for missing strings.
- setup_steps: EVERY item must be a real shell command the user can copy-paste and run.
  Include explicit installation commands for the detected tech stack (e.g., pip install, npm install) 
  and any necessary environment setup.
  - IMPORTANT: Use the detected configuration files (e.g. pyproject.toml, package.json, Cargo.toml) as the primary source for installation commands. 
    If you see 'pyproject.toml', use it instead of assuming 'requirements.txt' exists.
  BAD:  "Install dependencies"
  GOOD: "pip install -r requirements.txt" (only if requirements.txt is actually in the file list)
  GOOD: "pip install ." (if pyproject.toml or setup.py is present)
  GOOD: "pip install fastapi uvicorn"
  BAD:  "Configure environment variables"
  GOOD: "cp .env.example .env"
- If you cannot find real commands, use the most likely ones based on the detected ecosystem.
- tech_stack: list specific names and versions, not categories.
- api_endpoints: only include endpoints you can actually see in the provided code.\
"""

_MINIMAL_INSTRUCTIONS = """\
Focus only on the essentials:
- purpose: one sentence maximum
- setup_steps: the minimum commands to get it running (3-5 steps)
- usage_examples: one primary example only
- Skip api_endpoints and env_variables unless critical to basic usage\
"""
 
_STANDARD_INSTRUCTIONS = """\
Cover all major sections with moderate detail:
- purpose: one clear sentence
- how_it_works: 2-3 sentences on the architecture
- setup_steps: complete sequence from clone to running (4-8 steps)
- usage_examples: 2 realistic examples
- Include env_variables if any are visible
- Include api_endpoints if it's an API project\
"""
 
_PROFESSIONAL_INSTRUCTIONS = """\
Write polished, production-quality documentation:
- purpose: precise and compelling — explains the value proposition clearly
- how_it_works: thorough explanation of the architecture and design decisions (3-4 sentences)
- tech_stack: comprehensive list including dev tooling and infrastructure
- setup_steps: complete, copy-paste-ready commands with no gaps (every step explicit)
- usage_examples: 2-3 realistic examples showing the main workflows
- env_variables: every env var with a clear description and where to obtain the value
- api_endpoints: all visible endpoints with method, path, and what they return
- Be specific and accurate — no vague statements\
"""
 
_DETAILED_INSTRUCTIONS = """\
Generate maximum-detail documentation covering everything visible in the codebase:
- purpose: thorough explanation of what the project does, who it's for, and why it exists
- how_it_works: deep architectural explanation — data flow, key components, design patterns (4-5 sentences)
- tech_stack: every dependency with version and its role in the project
- prerequisites: every requirement including optional ones
- setup_steps: every single command in exact order — nothing omitted, nothing assumed
- usage_examples: 3+ examples covering different features and workflows
- env_variables: exhaustive list with descriptions, example values, and whether required or optional
- api_endpoints: all endpoints with method, path, parameters, and response description
- scripts: every script/command available with what it does\
"""
 
_TEMPLATE_INSTRUCTIONS = {
    "minimal":      _MINIMAL_INSTRUCTIONS,
    "standard":     _STANDARD_INSTRUCTIONS,
    "professional": _PROFESSIONAL_INSTRUCTIONS,
    "detailed":     _DETAILED_INSTRUCTIONS,
    "default":      _STANDARD_INSTRUCTIONS,   # alias
}
 
_USER_TEMPLATE = """\
{instructions}
 
Return a JSON object matching this exact schema:
 
{schema}
 
=== REPOSITORY CONTEXT ===
{context}\
"""


# Public API

def build(context: str, template: str = "standard") -> tuple[str, str]:
    instructions = _TEMPLATE_INSTRUCTIONS.get(template, _STANDARD_INSTRUCTIONS)
    user_prompt  = _USER_TEMPLATE.format(
        instructions=instructions,
        schema=_SCHEMA,
        context=context,
    )
    return _SYSTEM, user_prompt

def build_from_snapshot(snapshot: RepoSnapshot, template: str = "standard") -> tuple[str, str]:
    """Convenience wrapper — builds context then prompts in one call."""
    from .context import build as build_context
    context = build_context(snapshot)
    return build(context, template=template)


# Diagnostic helpers

def char_counts(context: str, template: str = "standard") -> tuple[str, str]:
    """
    Rough budget guide:
      codellama:7b  → 4,096 token context window  (~16,000 chars total)
      mistral:7b    → 8,192 token context window  (~32,000 chars total)
      llama3.2:3b   → 8,192 token context window  (~32,000 chars total)
      groq llama3   → 8,192 token context window  (~32,000 chars total)

    """
    system, user = build(context, template)
    total = len(system) + len(user)
    return {
        "system_tokens_est": len(system) // 4,
        "user_tokens_est":   len(user) // 4,
        "total_tokens_est":  total // 4,
        "fits_codellama_7b": (total // 4) < 3_500,
        "fits_mistral_7b":   (total // 4) < 7_500,
    }
