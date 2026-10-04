"""
AST Parser for Python source files.

Extracts:
  - Functions (name, start_line, end_line, docstring, calls)
  - Classes (name, start_line, end_line, methods, docstring)
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

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "docstring": self.docstring,
            "calls": self.calls,
        }


@dataclass
class ClassInfo:
    name: str
    start_line: int
    end_line: int
    methods: list[FunctionInfo] = field(default_factory=list)
    docstring: str | None = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "docstring": self.docstring,
            "methods": [m.to_dict() for m in self.methods],
        }


@dataclass
class ParsedFile:
    file: str = ""                      # relative or absolute path
    functions: list[FunctionInfo] = field(default_factory=list)
    classes: list[ClassInfo] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    calls: list[str] = field(default_factory=list)
    file_path: str = ""

    def __post_init__(self) -> None:
        if not self.file and self.file_path:
            self.file = self.file_path
        elif not self.file_path and self.file:
            self.file_path = self.file

    def to_dict(self) -> dict:
        return parsed_file_to_dict(self)


def _extract_calls(node: ast.AST) -> list[str]:
    """Collect all Call node names inside a function/class body."""
    calls: list[str] = []
    body = getattr(node, "body", None)
    nodes_to_walk = body if isinstance(body, list) else [node]
    for stmt in nodes_to_walk:
        for child in ast.walk(stmt):
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
    methods: list[FunctionInfo] = []
    for item in node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            methods.append(_parse_function(item))
    return ClassInfo(
        name=node.name,
        start_line=start_line,
        end_line=end_line,
        methods=methods,
        docstring=ast.get_docstring(node),
    )


def _parse_imports(node: ast.AST) -> list[str]:
    imports: list[str] = []
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
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return []
    calls: list[str] = []
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name):
            calls.append(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            calls.append(node.func.attr)
    for child in ast.iter_child_nodes(node):
        calls.extend(_extract_top_level_calls(child))
    return calls


def parse_source(source: str, filename: str = "<string>") -> ParsedFile:
    """Parse a string of Python source code and return a structured ParsedFile."""
    try:
        tree = ast.parse(source, filename=filename)
    except Exception:
        return ParsedFile(file=filename)

    parsed = ParsedFile(file=filename)
    parsed.imports = _parse_imports(tree)

    top_level_calls: list[str] = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            parsed.classes.append(_parse_class(node))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            parsed.functions.append(_parse_function(node))
        else:
            top_level_calls.extend(_extract_top_level_calls(node))

    parsed.calls = list(dict.fromkeys(top_level_calls))  # deduplicate, preserve order
    return parsed


def parse_file(filepath: Path | str) -> ParsedFile:
    """Parse a single Python file and return a structured ParsedFile."""
    filepath = Path(filepath)
    try:
        source = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ParsedFile(file=str(filepath))
    return parse_source(source, filename=str(filepath))


def parsed_file_to_dict(pf: ParsedFile) -> dict:
    """Convert a ParsedFile dataclass to a plain dict (JSON-serializable)."""
    return {
        "file": pf.file,
        "file_path": pf.file_path,
        "functions": [f.to_dict() for f in pf.functions],
        "classes": [c.to_dict() for c in pf.classes],
        "imports": pf.imports,
        "calls": pf.calls,
    }

