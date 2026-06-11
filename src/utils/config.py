from pathlib import Path
import json 

def _file_config() -> Path:
    here = Path(__file__).resolve()

    for parent in [here.parent, here.parent.parent, here.parent.parent.parent, here.parent.parent.parent.parent]:
        candidate = parent / "config.json"
        if candidate.exists():
            return candidate
    
    raise FileNotFoundError(
        "config.json not found. Re-install the package or run from the project root"
    )

def load(section: str | None = None) -> dict:
    """Load config.json, optionally returning only one section"""
    #path = _find_config()
    #with open (path, encoding="utf-8") as f:
    #    data = json.load(f)
    
    #return data[section] if section else data

# cache
_CACHE: dict | None = None

def get(section: str | None = None) -> dict:
    global _CACHE
    if _CACHE is None:
        _CACHE = load()
    return _CACHE[section] if section else _CACHE

