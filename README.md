# readmegen



**AI-powered README generator. Point it at any repo.**

`readmegen` scans a codebase, understands what it does, and writes a complete, professional `README.md` — in seconds, from your terminal, for free.

```bash
pip install readmegen
readmegen generate ./your-project
```

<!--
  Terminal demo placeholder — record with asciinema or terminalizer and embed here:
  asciinema rec demo.cast
  asciinema upload demo.cast
  Then embed:
  [![asciicast](https://asciinema.org/a/XXXXX.svg)](https://asciinema.org/a/XXXXX)
-->

![readmegen demo](https://raw.githubusercontent.com/yourusername/readmegen/main/docs/demo.gif)

---

## Why This Exists

Every project needs a README. Almost nobody enjoys writing one.

The result: thousands of repositories with a README that's either missing, three lines long, or six months out of date the moment the codebase moves on. Documentation debt is one of the most common and most avoidable forms of technical debt — and it's almost always skipped not because it's hard, but because it's tedious.

`readmegen` removes the tedium. It reads your actual code — your entry points, your dependencies, your project structure — and writes documentation grounded in what's really there, not a generic template with blanks to fill in.

It runs entirely on your terminal, costs nothing to use, and never sends your code anywhere if you choose to run it locally with Ollama.

---

## How It Works

`readmegen` runs a three-phase pipeline every time you generate a README:

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   Scanner    │ ───▶ │   Analyzer   │ ───▶ │    Writer    │
│  (Phase 1)   │      │  (Phase 2)   │      │  (Phase 3)   │
└─────────────┘      └─────────────┘      └─────────────┘
 reads your repo       sends context to     renders a clean
 detects languages,    an LLM, gets back     README.md from
 frameworks, deps      structured analysis   the structured data
```

1. **Scan** — walks your project, respects `.gitignore`, detects the primary language, identifies frameworks from `package.json` / `requirements.txt` / `Cargo.toml` / `go.mod` and others, and extracts your dependency list.
2. **Analyze** — builds a token-budgeted context from the most relevant files (entry points first), sends it to an LLM backend, and parses the response into structured fields: purpose, setup steps, tech stack, environment variables, API endpoints, and more.
3. **Write** — renders that structured data into clean Markdown using one of four built-in templates, and writes it to `README.md` — backing up any existing one first.

Nothing about your code is stored or sent anywhere beyond the single model call required to analyze it. If you run the local Ollama backend, nothing leaves your machine at all.

---

## Installation

```bash
pip install readmegen
```

Requires **Python 3.11+**.

---

## Backend Setup

`readmegen` needs one model backend to generate the analysis. Choose whichever fits you — both are free.

### Option A — Groq (cloud, zero install, recommended for quick start)

1. Create a free account and API key at **[console.groq.com](https://console.groq.com)**
2. Add it to a `.env` file in your project directory:

   ```bash
   echo "GROQ_API_KEY=your_key_here" > .env
   ```

3. Done. Groq's free tier allows 14,400 requests/day — far more than typical use requires.

### Option B — Ollama (local, fully private, no API key)

1. Install Ollama: **[ollama.com](https://ollama.com)**
2. Pull the model:

   ```bash
   ollama pull codellama:7b
   ```

3. Ollama runs a local server automatically. `readmegen` detects it and uses it — no further setup needed.

Check which backend is active at any time:

```bash
readmegen status
```

```
╭─────────────────── Backend Status ───────────────────╮
│  Ollama:    ✓ Running   model codellama:7b ready      │
│  Groq:      ✗ No GROQ_API_KEY                         │
│  Will use:  Ollama (codellama:7b)                     │
╰────────────────────────────────────────────────────────╯
```

---

## Usage

### Generate a README

```bash
readmegen generate ./your-project
```

You'll be prompted to choose a template style:

```
  1. Minimal       Title, About, Installation, Usage, License
  2. Standard      All sections, moderate detail
  3. Professional  Polished, production-quality, full detail
  4. Detailed      Maximum depth, table of contents, exhaustive
```

Or skip the prompt entirely by specifying one directly:

```bash
readmegen generate ./your-project --template professional
```

### Preview without writing

```bash
readmegen generate ./your-project --dry-run
```

Renders the full README in your terminal — nothing touches disk.

### Custom output path

```bash
readmegen generate ./your-project --output ./docs/README.md
```

### Scan only (Phase 1, no model call)

```bash
readmegen scan ./your-project
```

Useful for quickly inspecting what `readmegen` detects — languages, frameworks, dependencies — without spending a model call.

### Force a fresh run

```bash
readmegen generate ./your-project --no-cache
```

By default, `readmegen` caches the scan and analysis results in `.readmegen/`. Use `--no-cache` to bypass the cache and re-run the full pipeline.

---

## Example Output

Running `readmegen generate` on a FastAPI + PostgreSQL project produces something like:

```markdown
# My Task API

![Language](...) ![License](...)

## About
A REST API for managing tasks, built with FastAPI and PostgreSQL.

## How It Works
Requests are routed through FastAPI, validated with Pydantic, and
persisted via SQLAlchemy. Authentication uses JWT tokens.

## Installation
1. Run:
   ```bash
   git clone https://github.com/you/my-task-api
   ```
2. Run:
   ```bash
   pip install -r requirements.txt
   ```
3. Run:
   ```bash
   uvicorn main:app --reload
   ```

## Environment Variables
| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `SECRET_KEY` | JWT signing secret |

## API Reference
- `GET /tasks` — list all tasks
- `POST /tasks` — create a new task

## License
MIT
```

That's a README most developers would commit without editing.

---

## Supported Ecosystems

`readmegen` detects dependencies and frameworks across:

| Ecosystem | Files Parsed |
|---|---|
| Python | `requirements.txt`, `pyproject.toml`, `Pipfile` |
| Node.js / TypeScript | `package.json` |
| Rust | `Cargo.toml` |
| Go | `go.mod` |
| Ruby | `Gemfile` |
| Java | `pom.xml` |

Framework detection covers 50+ common libraries — FastAPI, Django, Flask, React, Next.js, Vue, Express, Rails, Spring Boot, and many more — automatically surfaced in the generated README's tech stack section.

---

## Command Reference

| Command | Description |
|---|---|
| `readmegen generate <path>` | Full pipeline — scan, analyze, write README |
| `readmegen scan <path>` | Phase 1 only — inspect detected languages/deps |
| `readmegen status` | Check which model backend is active |
| `readmegen --version` | Show installed version |

### Flags

| Flag | Applies to | Description |
|---|---|---|
| `--template`, `-t` | `generate` | `minimal`, `standard`, `professional`, `detailed`, or a path to a custom `.md` template |
| `--output`, `-o` | `generate` | Custom output path (default: `<path>/README.md`) |
| `--dry-run` | `generate` | Preview in terminal, write nothing |
| `--no-cache` | `generate`, `scan` | Force a fresh scan/analysis, ignoring `.readmegen/` cache |
| `--verbose`, `-v` | `scan` | Show every file collected, with skip reasons |

---

## Privacy

If you use the **Ollama** backend, your code never leaves your machine. The entire analysis runs locally.

If you use **Groq**, a trimmed, token-budgeted excerpt of your repository (entry points, config files, and key source files — not your full codebase) is sent to Groq's API for analysis. No data is stored by `readmegen` itself, and nothing is sent anywhere outside of that single API call per run.

---

## Contributing

Pull requests are welcome. For larger changes, please open an issue first to discuss what you'd like to change.

```bash
git clone https://github.com/yourusername/readmegen
cd readmegen
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

---

## License

[MIT](LICENSE)
