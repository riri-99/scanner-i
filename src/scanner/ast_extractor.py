from __future__ import annotations

from dataclasses import dataclass

from .ast_loader import get_parser
from .ast_queries import run_query, BODY_KINDS

# RESULT MODEL

@dataclass
class SkeletonResult:
    skeleton: str
    was_extracted: bool
    fallback_reason: str


# Public API

def extract_skeleton(content: str, readmegen_lang: str) -> SkeletonResult:

    lang_key = readmegen_lang.lower()
    code = content.encode("utf-8", errors="ignore")

    parser = get_parser(lang_key)
    if parser is None:
        return SkeletonResult("", False, f"no parser available for '{readmegen_lang}'")
    
    try:
        tree = parser.parse(code)
    except Exception as e:
        return SkeletonResult("", False, f"parse failed: {e}")
    
    captures = run_query(lang_key, tree, code)
    if not captures:
        return SkeletonResult("", False, f"no query available for '{readmegen_lang}'")
    
    body_types = set(BODY_KINDS.get(lang_key, []))

    imports = captures.get("import", [])
    functions = captures.get("function", [])
    classes = captures.get("class", [])
    comments = captures.get("comment", [])


    if not functions and not classes and not imports:
        return SkeletonResult("", False, "no structural nodes matched")
    
    sections = []

    # IMPORTS
    if imports:
        import_lines = [_node_text(n, code) for n in imports]
        sections.append("\n".join(import_lines))

    # CLASSES
    for node in sorted(classes, key= lambda n: n.start_byte):
        sig = _extract_signature(node, code, body_types)
        doc = _find_attached_doc(node, code, comments, body_types)
        block = sig
        if doc:
            block += f"\n   {doc}"
        sections.append(block)

    # FUnctions/ methods
    for node in sorted(functions, key= lambda n: n.start_byte):
        sig = _extract_signature(node, code, body_types)
        doc = _find_attached_doc(node, code, comments, body_types)
        block = sig
        if doc:
            block += f"\n   {doc}"
        block += f"\n   ..."
        sections.append(block)

    skeleton = "\n\n".join (s for s in sections if s.strip())
    return SkeletonResult(skeleton, True, "")


# SIgnature extraction

def _extract_signature(node, code: bytes, body_types: set[str]) -> str:

    body_node = _find_body_child(node, body_types)

    if body_node is None:
        return _node_text(node, code).strip()
    
    sig_bytes = code[node.start_byte: body_node.start_byte]
    return sig_bytes.decode("utf-8", errors="ignore").strip()

def _find_body_child(node, body_types: set[str]):

    # find the body child of a function or a class node
    if not body_types:
        return None
    
    for child in node.children:
        if child.type in body_types:
            return child
    
    for child in node.children:
        for grandchild in child.children:
            if grandchild.type in body_types:
                return grandchild
            
    return None

    
# COmment attachment

def _find_attached_doc(node, code: bytes, comments: list, body_types: set[str]) -> str:

    # Pattern 1: doctring as firt statement (as in Python)
    body_node = _find_body_child(node, body_types)
    if body_node is not None and body_node.children:
        first = body_node.children[0]

        text = code[first.start_byte:first.end_byte].decode("utf-8", errors="ignore")
        if first.type in ("expression_statement", "string", "string_literal") and ('"""' in text or "'''" in text or (
            text.strip().startswith(('"', "'")) and text.strip().endswith(('"', "'"))
        )):
            return _clean_doc_text(text)
        
    # Pattern 2: Comment preceeding the definition
    node_start_row = node.start_point[0]
    best = None
    for c in comments:
        c_end_row = c.end_point[0]

        if c_end_row == node_start_row - 1:
            best = c
            break
    
    if best is not None:
        text = code[best.start_byte:best.end_byte].decode("utf-8", errors="ignore")
        return _clean_doc_text(text)
    
    return ""

def _clean_doc_text(text: str) -> str:

    text = text.strip()
    for marker in ('"""', "'''", "//", "/*", "*/", "#"):
        text = text.replace(marker, "")
    text = " ".join(text.split())
    return text[:140]

# Helpers

def _node_text(node, code: bytes) -> str:
    return code[node.start_byte:node.end_byte].decode("utf-8", errors="ignore").strip()

