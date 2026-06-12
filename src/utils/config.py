from pathlib import Path
import json 

_CONFIG_PATH = Path(__file__).parent.parent / "config.json"

_CACHE: dict | None = None

def get(section: str | None = None) -> dict:

    global _CACHE
    if _CACHE is None:
        if not _CONFIG_PATH.exists():
            raise FileNotFoundError(
                f"config.json not found at {_CONFIG_PATH}. \n"
                "Re-install the package: pip install --force-reinstall readmegen"
            )
        
        with open(_CONFIG_PATH, encoding = "utf-8") as f:
            _CACHE = json.load(f)
        
    return _CACHE[section] if section else _CACHE
