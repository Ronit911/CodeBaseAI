"""
AST Parser for Python source files.

Extracts:
  - Functions (name, start_line, end_line, docstring, calls)
  - Classes (name, start_line, end_line, methods)
  - Imports (module names)
  - Top-level function calls
"""

import ast
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FunctionInfo:
    name: str
    start_line: int
    end_line: int
    docstring: str | None = None
    calls: list[str] = field(default_factory=list)


@dataclass
class ClassInfo:
    name: str
    start_line: int
    end_line: int
    methods: list[FunctionInfo] = field(default_factory=list)


@dataclass
class ParsedFile:
    file: str                           # relative path
    functions: list[FunctionInfo] = field(default_factory=list)
    classes: list[ClassInfo] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    calls: list[str] = field(default_factory=list)


def _extract_calls(node: ast.AST) -> list[str]:
    """Collect all Call node names inside a function/class body."""
    calls = []
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            if isinstance(child.func, ast.Name):
                calls.append(child.func.id)
            elif isinstance(child.func, ast.Attribute):
                calls.append(child.func.attr)
    return list(dict.fromkeys(calls))  # deduplicate, preserve order


def _parse_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> FunctionInfo:
    start_line = node.decorator_list[0].lineno if node.decorator_list else node.lineno
    end_line = node.end_lineno or node.lineno
    if end_line < start_line:
        end_line = start_line
    return FunctionInfo(
        name=node.name,
        start_line=start_line,
        end_line=end_line,
        docstring=ast.get_docstring(node),
        calls=_extract_calls(node),
    )


def _parse_class(node: ast.ClassDef) -> ClassInfo:
    start_line = node.decorator_list[0].lineno if node.decorator_list else node.lineno
    end_line = node.end_lineno or node.lineno
    if end_line < start_line:
        end_line = start_line
    methods = []
    for item in node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            methods.append(_parse_function(item))
    return ClassInfo(
        name=node.name,
        start_line=start_line,
        end_line=end_line,
        methods=methods,
    )


def _parse_imports(node: ast.AST) -> list[str]:
    imports = []
    for child in ast.walk(node):
        if isinstance(child, ast.Import):
            for alias in child.names:
                imports.append(alias.name)
        elif isinstance(child, ast.ImportFrom):
            if child.module:
                imports.append(child.module)
            else:
                for alias in child.names:
                    imports.append(alias.name)
    return list(dict.fromkeys(imports))  # deduplicate, preserve order


def _extract_top_level_calls(node: ast.AST) -> list[str]:
    """Collect Call names from top-level statements, excluding function/class bodies."""
    calls = []
    stack = [node]
    while stack:
        curr = stack.pop()
        if isinstance(curr, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if isinstance(curr, ast.Call):
            if isinstance(curr.func, ast.Name):
                calls.append(curr.func.id)
            elif isinstance(curr.func, ast.Attribute):
                calls.append(curr.func.attr)
        stack.extend(ast.iter_child_nodes(curr))
    return calls


def parse_file(filepath: Path | str) -> ParsedFile:
    """Parse a single Python file and return a structured ParsedFile."""
    filepath = Path(filepath)
    try:
        source = filepath.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(filepath))
    except Exception:
        return ParsedFile(file=str(filepath))

    parsed = ParsedFile(file=str(filepath))
    parsed.imports = _parse_imports(tree)

    top_level_calls = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            parsed.classes.append(_parse_class(node))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            parsed.functions.append(_parse_function(node))
        else:
            top_level_calls.extend(_extract_top_level_calls(node))

    parsed.calls = list(dict.fromkeys(top_level_calls))  # deduplicate, preserve order
    return parsed


def parsed_file_to_dict(pf: ParsedFile) -> dict:
    """Convert a ParsedFile dataclass to a plain dict (JSON-serializable)."""
    return {
        "file": pf.file,
        "functions": [
            {
                "name": f.name,
                "start_line": f.start_line,
                "end_line": f.end_line,
                "docstring": f.docstring,
                "calls": f.calls,
            }
            for f in pf.functions
        ],
        "classes": [
            {
                "name": c.name,
                "start_line": c.start_line,
                "end_line": c.end_line,
                "methods": [
                    {
                        "name": m.name,
                        "start_line": m.start_line,
                        "end_line": m.end_line,
                        "docstring": m.docstring,
                        "calls": m.calls,
                    }
                    for m in c.methods
                ],
            }
            for c in pf.classes
        ],
        "imports": pf.imports,
        "calls": pf.calls,
    }

