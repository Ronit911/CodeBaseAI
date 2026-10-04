"""
CodeEntity schema — a single parsed symbol extracted from source code.

Produced by the AST parser and consumed by the chunker and graph builder.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel


class SymbolType(str, Enum):
    FUNCTION = "function"
    METHOD = "method"
    CLASS = "class"
    MODULE = "module"


class FunctionEntity(BaseModel):
    """A single function or method discovered by the AST parser."""
    name: str
    start_line: int
    end_line: int
    docstring: Optional[str] = None
    calls: list[str] = []


class ClassEntity(BaseModel):
    """A class discovered by the AST parser, with its methods."""
    name: str
    start_line: int
    end_line: int
    methods: list[FunctionEntity] = []


class ParsedFileEntity(BaseModel):
    """
    The complete parsed representation of one source file.
    Produced by ``parser.ast_parser.parser.parse_file``.
    """
    file_path: str                  # absolute or repo-relative path
    functions: list[FunctionEntity] = []
    classes: list[ClassEntity] = []
    imports: list[str] = []         # module names
    calls: list[str] = []           # top-level call names
