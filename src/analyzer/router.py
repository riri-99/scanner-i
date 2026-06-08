"""
Model Router

decision layer that picks the right model backend and returns a ready to use client.
the rest of the codebase calls get_client() and never need to know whether Ollama or Groq is running underneath.

Decision sequence: 
    1. If preferred == "ollama" (default):
       a. Ping Ollama at localhost:11434
       b. Check the requested model is pulled
       c. If both pass → return OllamaClient
       d. If Ollama is up but model missing → print pull instructions, exit
       e. If Ollama is not running → fall through to Groq
  2. Check for GROQ_API_KEY in environment
       a. If found → return GroqClient
  3. Neither available → print full setup guide, exit

"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import urllib.request
import urllib.error

from rich.console import Console
from rich.panel import Panel

from .base import ModelClient
from .ollama_client import OllamaClient
from .groq_client import GroqClient

# config

_CONFIG_PATH = Path(__file__).parent.parent.parent / "config.json"

with open(_CONFIG_PATH) as _f:
    _CFG = json.load(_f)["model"]

OLLAMA_HOST: str = _CFG["ollama_host"]
OLLAMA_MODEL: str = _CFG["ollama_model"]
GROQ_MODEL: str = _CFG["groq_model"]
TEMPERATURE: float = _CFG["temperature"]
TIMEOUT: int = _CFG["timeout_secs"]
PREFERRED: str = _CFG["preferred"]

console = Console()

# Publi API
def get_client() -> ModelClient:
    if PREFERRED == "groq":
        client = _try_groq()
        if client: 
            return client
        
        _exit_no_backend(ollama_running=False, ollama_model_missing=False)

    
    # Default - try ollama first, fall back to groq
    ollama_running, model_pulled = _check_ollama()

    if ollama_running and model_pulled:
        console.print(f"  [dim]Using[/dim] [green]Ollama[/green] [dim]({OLLAMA_MODEL})[/dim]")
        return OllamaClient(
            host = OLLAMA_HOST,
            model = OLLAMA_MODEL,
            temperature = TEMPERATURE,
            timeout = TIMEOUT,
        )
    
    if ollama_running and not model_pulled:
        # pull and exit, no local setup 
        _exit_model_not_pulled()

    client = _try_groq()
    if client:
        console.print(f"  [dim]Ollama not running — using[/dim] [cyan]Groq[/cyan] [dim]({GROQ_MODEL})[/dim]")
        return client
    
    _exit_no_backend(ollama_running=False, ollama_model_missing=False)


# Ollama checks

def _check_ollama() -> tuple[bool, bool]:
    try:
        url = f"{OLLAMA_HOST}/api/tags"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "readmegen/0.1.0"},
            method="GET"
        )

        with urllib.request.urlopen(req, timeout=2) as resp:
            if resp.status != 200:
                return False, False
            data = json.loads(resp.read().decode())

        pulled_models = [m["name"] for m in data.get("models", [])]
        model_pulled = any(
            OLLAMA_MODEL in name or name in OLLAMA_MODEL
            for name in pulled_models
        )
        return True, model_pulled
    
    except (urllib.error.URLError, TimeoutError, OSError):
        return False, False
    
    except Exception:
        return False, False
    

# Groq check

def _try_groq() -> GroqClient | None:
    _load_dotenv()
    api_key = os.environ.get("GROQ_API_KEY", "").strip()

    if not api_key:
        return None
 
    return GroqClient(
        model=GROQ_MODEL,
        temperature=TEMPERATURE,
    )
 
 
def _load_dotenv() -> None:
    env_path = Path.cwd() / ".env"
    if not env_path.exists():
        return
 
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key   = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


# Exit helpers

def _exit_model_not_pulled() -> None:
    msg = (
        f"[yellow]Ollama is running but [bold]{OLLAMA_MODEL}[/bold] is not pulled yet.[/yellow]\n\n"
        f"Run this once to download the model (~4 GB):\n\n"
        f"  [bold cyan]ollama pull {OLLAMA_MODEL}[/bold cyan]\n\n"
        f"Or use Groq as a free cloud fallback — add this to your [dim].env[/dim] file:\n\n"
        f"  [bold cyan]GROQ_API_KEY=your_key_here[/bold cyan]\n\n"
        f"Get a free Groq key at [dim]https://console.groq.com[/dim]"
    )
    console.print(Panel(msg, title="[bold yellow]Model not found[/bold yellow]", border_style="yellow"))
    sys.exit(1)
 
 
def _exit_no_backend(ollama_running: bool, ollama_model_missing: bool) -> None:
    msg = (
        "[red]No model backend is available.[/red]\n\n"
        "[bold]Option 1 — Run locally with Ollama (recommended, free):[/bold]\n\n"
        "  1. Install Ollama:  [cyan]https://ollama.com[/cyan]\n"
        f"  2. Pull the model:  [bold cyan]ollama pull {OLLAMA_MODEL}[/bold cyan]\n"
        "  3. Ollama starts automatically — then re-run readmegen.\n\n"
        "[bold]Option 2 — Use Groq (free cloud fallback):[/bold]\n\n"
        "  1. Get a free API key at [cyan]https://console.groq.com[/cyan]\n"
        "  2. Create a [dim].env[/dim] file in your project:\n\n"
        "       [bold cyan]GROQ_API_KEY=your_key_here[/bold cyan]\n\n"
        "  3. Re-run readmegen."
    )
    console.print(Panel(msg, title="[bold red]No model backend found[/bold red]", border_style="red"))
    sys.exit(1)

# Status helper

def status() -> dict:
    """
    Returns a dict describing the current backend availability.
    Used by the CLI to show backend status without actually selecting one.
    """
    ollama_running, model_pulled = _check_ollama()
    _load_dotenv()
    groq_key = bool(os.environ.get("GROQ_API_KEY", "").strip())
 
    return {
        "ollama_running":    ollama_running,
        "ollama_model":      OLLAMA_MODEL,
        "ollama_model_ready": model_pulled,
        "groq_available":    groq_key,
        "groq_model":        GROQ_MODEL,
        "preferred":         PREFERRED,
        "will_use":          (
            "ollama" if (ollama_running and model_pulled) else
            "groq"   if groq_key else
            "none"
        ),
    }