from __future__ import annotations

from tree_sitter import Query, QueryCursor

from .ast_loader import get_language

# per-language node type mappping

NODE_KINDS: dict[str, dict[str, list[str]]] = {
    "python": {
        "imports":   ["import_statement", "import_from_statement"],
        "functions": ["function_definition"],
        "classes":   ["class_definition"],
        "comments":  ["comment"],
    },
    "javascript": {
        "imports":   ["import_statement"],
        "functions": ["function_declaration", "method_definition"],
        "classes":   ["class_declaration"],
        "comments":  ["comment"],
    },
    "typescript": {
        "imports":   ["import_statement"],
        "functions": ["function_declaration", "method_definition"],
        "classes":   ["class_declaration", "interface_declaration"],
        "comments":  ["comment"],
    },
    "tsx": {
        "imports":   ["import_statement"],
        "functions": ["function_declaration", "method_definition"],
        "classes":   ["class_declaration", "interface_declaration"],
        "comments":  ["comment"],
    },
    "go": {
        "imports":   ["import_declaration"],
        "functions": ["function_declaration", "method_declaration"],
        "classes":   ["type_declaration"],
        "comments":  ["comment"],
    },
    "rust": {
        "imports":   ["use_declaration"],
        "functions": ["function_item"],
        "classes":   ["struct_item", "enum_item", "trait_item", "impl_item"],
        "comments":  ["line_comment", "block_comment"],
    },
    "java": {
        "imports":   ["import_declaration"],
        "functions": ["method_declaration", "constructor_declaration"],
        "classes":   ["class_declaration", "interface_declaration"],
        "comments":  ["line_comment", "block_comment"],
    },
    "kotlin": {
        "imports":   ["import"],
        "functions": ["function_declaration"],
        "classes":   ["class_declaration"],
        "comments":  ["line_comment", "multiline_comment"],
    },
    "ruby": {
        "imports":   ["call"],   # filtered further: only require/require_relative calls
        "functions": ["method"],
        "classes":   ["class", "module"],
        "comments":  ["comment"],
    },
    "php": {
        "imports":   ["namespace_use_declaration"],
        "functions": ["function_definition", "method_declaration"],
        "classes":   ["class_declaration", "interface_declaration"],
        "comments":  ["comment"],
    },
    "c#": {
        "imports":   ["using_directive"],
        "functions": ["method_declaration", "constructor_declaration"],
        "classes":   ["class_declaration", "interface_declaration"],
        "comments":  ["comment"],
    },
    "c++": {
        "imports":   ["preproc_include"],
        "functions": ["function_definition"],
        "classes":   ["class_specifier", "struct_specifier"],
        "comments":  ["comment"],
    },
    "c": {
        "imports":   ["preproc_include"],
        "functions": ["function_definition"],
        "classes":   ["struct_specifier"],
        "comments":  ["comment"],
    },
    "swift": {
        "imports":   ["import_declaration"],
        "functions": ["function_declaration"],
        "classes":   ["class_declaration"],
        "comments":  ["comment", "multiline_comment"],
    },
    "shell": {
        "imports":   [],   # shell has no import concept worth extracting
        "functions": ["function_definition"],
        "classes":   [],   # shell has no class concept
        "comments":  ["comment"],
    },
}

# Query builder

_QUERY_CACHE: dict[str, Query | None] = {}

def build_query(readmegen_lang: str) -> Query | None:

    key = readmegen_lang.lower()

    if key in _QUERY_CACHE:
        return _QUERY_CACHE[key]
    
    kinds = NODE_KINDS.get(key)
    if kinds is None:
        _QUERY_CACHE[key] = None
        return None
    
    lang = get_language(key)
    if lang is None:
        _QUERY_CACHE[key] = None
        return None
    
    pattern = _build_pattern(kinds)
    if not pattern:
        _QUERY_CACHE[key] = None
        return None
    
    try:
        query = Query(lang, pattern)
    except Exception:
        query = None

    _QUERY_CACHE[key] = query
    return query

def _build_pattern(kinds: dict[str, list[str]]) -> str:

    lines = []
    for category, node_types in kinds.items():
        if not node_types:
            continue
        capture_name = category[:-1] if category.endswith("s") else category
        alternation = " ".join(f"({int})" for nt in node_types)
        lines.append(f"[{alternation}] @{capture_name}")
    
    return "\n".join(lines)

# Query runner

def run_query(readmegen_lang: str, tree, code: bytes) -> dict[str, list]:

    query = build_query(readmegen_lang)
    if query is None:
        return {}
    
    cursor = QueryCursor(query)
    captures = cursor.captures(tree.root_node)

    return {name: nodes for name, nodes in captures.items()}

# Helper

def supported_languages() -> list[str]:
    return sorted(NODE_KINDS.keys())

