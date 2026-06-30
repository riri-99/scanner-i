"""
Prompt Builder

2 design principle here:
    1. JSON schema in the prompt — the model fills in the schema like a form rather than free writing.
    2. Strict output contract in the system prompt - gives raw json only.

"""

from __future__ import annotations

from ..scanner.assembler import RepoSnapshot
from .context import build as build_context


# Output schema
# written as a json-like string rather than a python dict so it reads naturally inside the prompt and the model sees exactly what format is expected.

_SCHEMA = """{
  "tagline": "One punchy, marketing-quality sentence that captures the project's value. Bold, confident, no fluff. e.g. 'The AI-powered README generator you'll actually use.'",
  "purpose": "One precise, functional sentence: what does this project literally do and who is it for?",
  "problem_statement": "2-3 sentences written persuasively: what pain point or inefficiency does this solve, and why does that problem matter? Write like a thoughtful engineer explaining why they built this, not generic marketing copy.",
  "how_it_works": "2-4 sentences describing the architecture and how the main components fit together. Be specific about the actual flow, not generic.",
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
      "title": "Short label for what this example demonstrates, e.g. 'Generate a README'",
      "command": "The exact runnable command or code snippet",
      "description": "One sentence explaining what this does and why you'd use it"
    }
  ],
  "command_reference": [
    {
      "command": "The exact command/subcommand signature, e.g. 'readmegen generate <path>'",
      "description": "One clear sentence on what this command does"
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
You are a senior software engineer and technical writer producing a README good enough to publish on a popular open-source project's GitHub page — the kind of README that makes a stranger want to star the repo and try it in the next two minutes.
 
Analyze the repository context and extract structured information for a README file.
 
Critical output rules — follow exactly:
- Return ONLY a raw JSON object. No preamble, no explanation, no markdown fences (no ```json).
- Every field must be present. Use [] for empty lists, {} for empty objects, and null for missing strings.
 
- tagline: write like a product landing page, not a Wikipedia summary. Confident, specific, no hedging words like "a tool that might help with...". One sentence, no period needed if it reads like a headline.
 
- problem_statement: this is NOT the same as purpose. purpose says what the tool does mechanically; problem_statement explains WHY someone would want it — the pain point, the tedious thing it replaces, the time it saves. Write it like you're convincing a skeptical developer in two sentences why this project exists at all.
 
- setup_steps: EVERY item must be a real shell command the user can copy-paste and run.
  BAD:  "Install dependencies"
  GOOD: "pip install -r requirements.txt"
  BAD:  "Configure environment variables"
  GOOD: "cp .env.example .env"
  If you cannot find real commands, use the most likely ones based on the detected ecosystem.
 
- usage_examples: each one needs a short title, the exact runnable command, and a one-sentence description of what it accomplishes — not just the bare command with no context.
 
- command_reference: ONLY populate this if the project is a CLI tool (has a command-line entry point, subcommands, or a `bin`/console_scripts setup visible in the context). For non-CLI projects (web APIs, libraries, scripts with no subcommands), return an empty list — do not invent commands that don't exist.
 
- tech_stack: list specific names and versions, not categories (e.g. "FastAPI 0.100", never "a web framework").
- api_endpoints: only include endpoints you can actually see in the provided code.
- Never use placeholder or generic language anywhere in the output. Every sentence should sound like it was written by someone who actually read this specific codebase.\
"""


_MINIMAL_INSTRUCTIONS = """\
Focus only on the essentials:
- tagline: one sentence, sharp and confident
- purpose: one sentence maximum
- problem_statement: skip this — leave it empty for minimal output
- setup_steps: the minimum commands to get it running (3-5 steps)
- usage_examples: one primary example only, with title + command + one-line description
- command_reference: skip unless this is clearly a CLI tool with 2+ distinct commands
- Skip api_endpoints and env_variables unless critical to basic usage\
  """
"""\
Focus only on the essentials:
- purpose: 2-3 sentences
- setup_steps: the minimum commands to get it running
- usage_examples: realistic examples showing the main workflow
- Skip api_endpoints and env_variables unless critical to basic usage
- Add a fallback "Getting Started" combined section that merges prerequisites + installation \
"""
 
_STANDARD_INSTRUCTIONS = """\
Cover all major sections with moderate detail:
- tagline: one clear, confident sentence
- purpose: one clear sentence
- problem_statement: 1-2 sentences — brief but real, not generic
- how_it_works: 2-3 sentences on the architecture
- setup_steps: complete sequence from clone to running (4-8 steps)
- usage_examples: 2 realistic examples, each with title + command + description
- command_reference: include if this is a CLI tool with multiple commands
- Include env_variables if any are visible
- Include api_endpoints if it's an API project\
"""
"""\
Cover all major sections with moderate detail:
- purpose: precise and compelling — explains the value proposition clearly. Be specific, mention the domain and the problem it solves
- how_it_works: 2-3 sentences on the architecture
- setup_steps: complete sequence from clone to running 
- usage_examples: 2 realistic examples
- Include env_variables if any are visible
- Include api_endpoints if it's an API project\
"""
 
_PROFESSIONAL_INSTRUCTIONS = """\
Write polished, production-quality documentation — the standard you'd expect from a well-maintained open source project with thousands of stars:
- tagline: landing-page quality, the line that would headline the project's GitHub page
- purpose: precise and compelling — explains the value proposition clearly
- problem_statement: 2-3 sentences, genuinely persuasive — the "why this exists" a maintainer would write
- how_it_works: thorough explanation of the architecture and design decisions (3-4 sentences)
- tech_stack: comprehensive list including dev tooling and infrastructure
- setup_steps: complete, copy-paste-ready commands with no gaps (every step explicit)
- usage_examples: 2-3 realistic examples, each with a real title, exact command, and clear description
- command_reference: full table if this is a CLI tool — every command/subcommand with description
- env_variables: every env var with a clear description and where to obtain the value
- api_endpoints: all visible endpoints with method, path, and what they return
- Be specific and accurate — no vague statements, no generic filler sentences anywhere\
"""
"""\
Write polished, production-quality documentation in a professional and academic tone:
- purpose: precise and compelling — explains the value proposition clearly. Be specific, mention the domain and the problem it solves.
- how_it_works: thorough explanation of the architecture and design decisions- data flow, key components, design patterns (7-8 sentences)
- tech_stack: comprehensive list including dev tooling and infrastructure. Must explain the role of each dependency in the project
- setup_steps: complete, copy-paste-ready commands with no gaps (every step explicit)
- usage_examples: 2-3 realistic examples showing the main workflows
- env_variables: every env var with a clear description and where to obtain the value
- api_endpoints: all visible endpoints with method, path, and what they return
- Be specific and accurate — no vague statements\
"""
 
_DETAILED_INSTRUCTIONS = """\
Generate maximum-detail documentation covering everything visible in the codebase:
- tagline: landing-page quality, confident and specific
- purpose: thorough explanation of what the project does, who it's for, and why it exists
- problem_statement: 3+ sentences — the full case for why this project exists, written persuasively
- how_it_works: deep architectural explanation — data flow, key components, design patterns (4-5 sentences)
- tech_stack: every dependency with version and its role in the project
- prerequisites: every requirement including optional ones
- setup_steps: every single command in exact order — nothing omitted, nothing assumed
- usage_examples: 3+ examples covering different features and workflows, each with title + command + description
- command_reference: exhaustive — every command, subcommand, and flag combination if this is a CLI tool
- env_variables: exhaustive list with descriptions, example values, and whether required or optional
- api_endpoints: all endpoints with method, path, parameters, and response description
- scripts: every script/command available with what it does\
"""
"""\
Generate maximum-detail documentation covering everything visible in the codebase. Every field must be present even if the list is empty:
- purpose: thorough explanation of what the project does, who it's for, and why it exists. Be specific, mention the domain and the problem it solves.
- how_it_works: deep architectural explanation — data flow, key components, design patterns (atleast one paragraph with 8-10 sentences)
- tech_stack: every dependency with version. write exact package names, not just categories. Must explain the role of each dependency in the project.
- prerequisites: every requirement including optional ones
- setup_steps: every single command in exact order — nothing omitted, nothing assumed
- usage_examples: 3+ examples covering different features and workflows. add commands, if any or explain the usage of the project properly in atleast 2-3 lines.
- env_variables: exhaustive list with descriptions, example values, and whether required or optional
- api_endpoints: all endpoints with method, path, parameters, and response description. look for @app.get, @router.post, app.use() patterns.
- scripts: every script/command available with what it does
Keep to every instruction in the template and give proper details for each section as mentioned.\
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
