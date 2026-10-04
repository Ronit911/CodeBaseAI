"""
CodeChunk schema — the canonical retrieval unit passed between all pipeline stages.

Parser → Chunker → Graph Builder → Embedder → Vector Store → BM25 Index
all operate on this common format so no stage needs to know the internals of another.
"""

import uuid
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class SymbolType(str, Enum):
    FUNCTION = "function"
    METHOD = "method"
    CLASS = "class"


class CodeChunk(BaseModel):
    """
    One retrieval unit representing a single meaningful symbol in source code.

    Fields
    ------
    chunk_id        : Unique identifier for this chunk (auto-generated).
    repository_id   : ID of the parent repository in PostgreSQL.
    file_path       : Absolute or repo-relative path to the source file.
    symbol_name     : Name of the function, method, or class (e.g. ``UserService.login``).
    symbol_type     : One of ``function``, ``method``, ``class``.
    start_line      : First line of the symbol (1-indexed).
    end_line        : Last line of the symbol (inclusive).
    code            : Raw source text of the symbol.
    extra           : Arbitrary extra metadata (calls, docstring, parent class, …).
    """

    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    repository_id: str
    file_path: str
    symbol_name: str
    symbol_type: SymbolType
    start_line: int
    end_line: int
    code: str
    extra: dict[str, Any] = Field(default_factory=dict)

    def citation(self) -> str:
        """Human-readable citation string, e.g. ``auth.py:20-38 (authenticate_user)``."""
        filename = self.file_path.split("/")[-1].split("\\")[-1]
        return f"{filename}:{self.start_line}-{self.end_line} ({self.symbol_name})"
