from __future__ import annotations

from tree_sitter import Language, Parser

# LAzy import plus cache

_LANGUAGE_CACHE = dict[str, Language | None] = {}

def get_language(readmegen_lang: str) -> Language | None:

    # return a tree sitter language object for a readmegen langauge
    key = readmegen_lang.lower()

    if key in _LANGUAGE_CACHE:
        return _LANGUAGE_CACHE[key]
    
    loader = _LOADERS.get(key)
    if loader is None:
        _LANGUAGE_CACHE[key] = None
        return None
    
    try:
        lang = Language(loader())
    except Exception:
        lang = None

    _LANGUAGE_CACHE[key] = lang
    return lang

def get_parser(readmegen_lang: str) -> Parser | None:
    
    # returns a ready to use parser or none
    lang = get_language(readmegen_lang)
    if lang is None:
        return None
    return Parser(lang)

# Per language laoder function

def _load_python():
    import tree_sitter_python as m
    return m.language()
 
def _load_javascript():
    import tree_sitter_javascript as m
    return m.language()
 
def _load_typescript():
    import tree_sitter_typescript as m
    return m.language_typescript()          # ← quirk: not .language()
 
def _load_tsx():
    import tree_sitter_typescript as m
    return m.language_tsx()                 # ← separate grammar for .tsx
 
def _load_go():
    import tree_sitter_go as m
    return m.language()
 
def _load_rust():
    import tree_sitter_rust as m
    return m.language()
 
def _load_java():
    import tree_sitter_java as m
    return m.language()
 
def _load_kotlin():
    import tree_sitter_kotlin as m
    return m.language()
 
def _load_ruby():
    import tree_sitter_ruby as m
    return m.language()
 
def _load_php():
    import tree_sitter_php as m
    return m.language_php()                 # ← quirk: not .language()
 
def _load_csharp():
    import tree_sitter_c_sharp as m
    return m.language()
 
def _load_cpp():
    import tree_sitter_cpp as m
    return m.language()
 
def _load_c():
    import tree_sitter_c as m
    return m.language()
 
def _load_swift():
    import tree_sitter_swift as m
    return m.language()
 
def _load_bash():
    import tree_sitter_bash as m
    return m.language()


# language to loader mapping

_LOADERS = {
    "python":     _load_python,
    "javascript": _load_javascript,
    "typescript": _load_typescript,
    "tsx":        _load_tsx,          # walker.py must pass "tsx" for .tsx files
    "go":         _load_go,
    "rust":       _load_rust,
    "java":       _load_java,
    "kotlin":     _load_kotlin,
    "ruby":       _load_ruby,
    "php":        _load_php,
    "c#":         _load_csharp,
    "c++":        _load_cpp,
    "c":          _load_c,
    "swift":      _load_swift,
    "shell":      _load_bash,
}


# Diagnostic helpers

def supported_languages() -> list[str]:
    return sorted(_LOADERS.keys())

def is_supported(readmegen_lang: str) -> bool:
    return readmegen_lang.lower() in _LOADERS
