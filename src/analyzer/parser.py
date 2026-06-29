# Takes whatever the model returns and makes it into a validated AnalysisObject.
# Never crashes - always returns something phase 3 can use, even if the model produced garbage.

""""
Parsing pipeline:
  1. Strip whitespace
  2. Strip ```json ... ``` fences
  3. Try json.loads() directly
  4. If that fails → extract first { ... } substring and retry
  5. If still failing → field-by-field regex extraction as last resort
  6. If all else fails → return a fallback AnalysisObject (parse_success=False)

"""

from __future__ import annotations

import json
import re
import logging
from typing import Any

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

# Analysis Object

class AnalysisObject(BaseModel):
    tagline:           str            = ""   # one punchy sentence, bold under the title
    purpose:           str            = ""   # functional one-liner: what it does
    problem_statement: str            = ""   # persuasive: why this exists, what pain it removes
    how_it_works:      str            = ""
    tech_stack:        list[str]      = Field(default_factory=list)
    prerequisites:     list[str]      = Field(default_factory=list)
    setup_steps:       list[str]      = Field(default_factory=list)
    usage_examples:    list[dict]     = Field(default_factory=list)  # [{"title","command","description"}]
    command_reference: list[dict]     = Field(default_factory=list)  # [{"command","description"}] — CLI tools only
    env_variables:     list[dict]     = Field(default_factory=list)
    api_endpoints:     list[str]      = Field(default_factory=list)
    scripts:           dict[str, str] = Field(default_factory=dict)
    license:            str | None    = None

    # Meta fields - set by the parser
    parse_success: bool = True # False if fallback was used
    parse_method: str = "" # such as - "direct" | "extracted" ... etc

    # Validators
    
    @field_validator("tech_stack", "prerequisites", "setup_steps", "api_endpoints", mode="before")

    @classmethod
    def ensure_str_list(cls, v: Any) -> list[str]:
        if v is None:
            return[]
        if isinstance(v, str):
            return [v] if v.strip() else []
        if isinstance(v, list):
            return[str(item).strip() for item in v if item and str(item).strip()]
        return[]
    

    @field_validator("env_variables", mode="before")

    @classmethod
    def ensure_dict_list(cls, v: Any) -> list[dict]:
        if not v or not isinstance(v, list):
            return[]
        result = []
        for item in v:
            if isinstance(item, dict) and item:
                result.append({
                    "name": str(item.get("name", item.get("key", "UNKNOWN"))),
                    "description": str(item.get("description", item.get("desc", ""))),
                })
        return result


    @field_validator("usage_examples", mode="before")

    @classmethod
    def ensure_usage_examples(cls, v: Any) -> list[dict]:
        if not v:
            return {}
        
        if isinstance(v, str):
            v = [v]
        result = []
        for item in v:
            if isinstance(item, dict):
                command = str(item.get("command", item.get("code", ""))).strip()
                if not command:
                    continue
                result.append({
                    "title": str(item.get("title", "")).strip(),
                    "command": command,
                    "description": str(item.get("description", "")).strip(),
                })
            elif isinstance(item, str) and item.strip():
                result.append({"title": "", "command": item.strip(), "description": ""})
        return result


    @field_validator("command_reference", mode="before")

    @classmethod
    def ensure_command_references(cls, v: Any) -> list[dict]:
        if not v or not isinstance(v, list):
            return []
        result = []
        for item in v:
            if isinstance(item, dict):
                command = str(item.get("command", "")).strip()
                if command:
                    result.append({
                        "command": command,
                        "description": str(item.get("description", "")).strip()
                    })
        return result
        

    @field_validator("scripts", mode="before")

    @classmethod
    def ensure_str_dict(cls, v: Any) -> dict[str, str]:
        if not v or not isinstance(v, dict):
            return{}
        return {str(k): str(val) for k, val in v.items() if k and val}
    

    @field_validator("tagline", "purpose", "problem_statement", "how_it_works", mode="before")

    @classmethod
    def ensure_str(cls, v: Any) -> str:
        if v is None:
            return ""
        return str(v).strip()
    

    @field_validator("license", mode="before")

    @classmethod
    def ensure_license(cls, v: Any) -> str | None:
        if not v or str(v).strip().lower() in ("null", "none", "unknown", ""):
            return None
        return str(v).strip()
    

# Public API

def parse(raw: str) -> AnalysisObject:
    # Parses a raw model response string into a validated AnalysisObject
    if not raw or not raw.strip():
        logger.warning("Parser received empty response - using fallback")
        return _fallback("empty response")
    
    # 1. clean the raw string
    cleaned = _strip_fences(raw.strip())

    # 2. direct json.loads
    result = _try_direct(cleaned)
    if result:
        return result
    
    # 3. extract first {...} substring
    result = _try_extract(cleaned)
    if result:
        return result
    
    # 4. field by field regex extraction
    result = _try_regex(cleaned)
    if result:
        return result
    
    #. give up
    logger.warning("All parse strategies failed. Raw Output: \n%s", raw[:500])
    return _fallback(f"unparsable output: {raw[:120]}...")


# Parsing stages

def _strip_fences(text: str) -> str:
    
    # removing markdown code fences
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s*```$",          "", text, flags=re.MULTILINE)

    brace_pos = text.find("{")
    if brace_pos > 0:
        preamble = text[:brace_pos]
        if not any(c in preamble for c in ['"', "[", "]", "}"]):
            text = text[brace_pos:]

    return text.strip()

def _try_direct(text: str) -> AnalysisObject | None:
    
    # straight json.loads on the cleaned text
    try:
        data = json.loads(text)
        obj = AnalysisObject(**_safe_extract(data))
        obj.parse_method = "direct"
        return obj
    except (json.JSONDecodeError, Exception):
        return None
    

def _try_extract(text: str) -> AnalysisObject | None:

    # handles the cases where the model added trailing text after the json.
    first = text.find("{")
    last = text.rfind("}")

    if first == -1 or last == -1 or last <= first:
        return None
    
    substring = text[first: last + 1]

    try:
        data = json.loads(substring)
        obj  = AnalysisObject(**_safe_extract(data))
        obj.parse_method = "extracted"
        return obj
    except (json.JSONDecodeError, Exception):
        return None
    

def _try_regex(text: str) -> AnalysisObject | None:

    try:
        fields: dict[str, Any] = {}

        # Extract simple string fields
        for field in ("purpose", "how_it_works", "license"):
            pattern = rf'"{field}"\s*:\s*"([^"]*)"'
            match = re.search(pattern, text, re.DOTALL)
            if match:
                fields[field] = match.group(1).strip()

        for field in ("tech_stack", "prerequisites", "setup_steps", "usage_examples", "api_endpoints"):
            pattern = rf'"{field}"\s*:\s*\[([^\]]*)\]'
            match = re.search(pattern, text, re.DOTALL)
            if match:
                items_raw = match.group(1)
                items = re.findall(r'"([^"]+)"', items_raw)
                if items:
                    fields[field] = items

        if not fields:
            return None
        
        obj = AnalysisObject(**fields)
        obj.parse_method = "regex"
        obj.parse_success = False
        return obj
    
    except Exception:
        return None
    

def _safe_extract(data: dict) -> dict:

    known = {"purpose", "how_it_works", "tech_stack", "prerequisites", "setup_steps", "usage_examples", " env_variables", "api_endpoints", "scripts", "license",}
    return {k: v for k, v in data.items() if k in known}

def _fallback(reason: str) -> AnalysisObject:
    
    return AnalysisObject(
        purpose       = "Could not determine — see raw model output.",
        how_it_works  = "",
        parse_success = False,
        parse_method  = f"fallback ({reason})",
    )
