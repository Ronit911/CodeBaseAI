"""
Code Chunker — creates retrieval units from ParsedFile objects.

Each chunk represents one meaningful symbol (function or class method)
and carries enough metadata to reconstruct citations.
"""

from dataclasses import dataclass, field
from pathlib import Path

from parser.ast_parser.parser import ParsedFile


@dataclass
class CodeChunk:
    file: str
    symbol: str
    symbol_type: str          # "function" | "method" | "class"
    start_line: int
    end_line: int
    code: str
    metadata: dict = field(default_factory=dict)
    chunk_id: str | None = None

    def __post_init__(self) -> None:
        if self.chunk_id is None:
            clean_path = self.file.replace("\\", "/")
            self.chunk_id = f"{clean_path}:{self.symbol}:{self.start_line}-{self.end_line}"

    @property
    def file_path(self) -> str:
        return self.file

    @property
    def symbol_name(self) -> str:
        return self.symbol

    def citation(self) -> str:
        """Human-readable citation string, e.g. ``auth.py:20-38 (authenticate_user)``."""
        filename = self.file.split("/")[-1].split("\\")[-1]
        return f"{filename}:{self.start_line}-{self.end_line} ({self.symbol})"

    def to_dict(self) -> dict:
        return chunk_to_dict(self)


def _extract_lines(filepath: str, start: int, end: int) -> str:
    """Read the raw source lines for a given line range."""
    try:
        lines = Path(filepath).read_text(encoding="utf-8", errors="replace").splitlines()
        start_idx = max(0, start - 1)
        end_idx = max(start_idx, end)
        return "\n".join(lines[start_idx : end_idx])
    except Exception:
        return ""


def chunk_parsed_file(parsed_file: ParsedFile, source: str | None = None) -> list[CodeChunk]:
    """
    Turn a ParsedFile into a list of CodeChunks.

    Strategy:
      - Each top-level function → 1 chunk
      - Each class method      → 1 chunk
      - Classes with no methods (data classes, etc.) → 1 chunk for the whole class
    """
    if not parsed_file:
        return []

    chunks: list[CodeChunk] = []
    filepath = getattr(parsed_file, "file", "") or getattr(parsed_file, "file_path", "")

    # Cache lines to avoid re-reading the file from disk for each symbol
    if source is not None:
        lines = source.splitlines()
    elif filepath:
        try:
            lines = Path(filepath).read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            lines = []
    else:
        lines = []

    def get_lines(start: int, end: int) -> str:
        if lines:
            start_idx = max(0, start - 1)
            end_idx = max(start_idx, end)
            return "\n".join(lines[start_idx : end_idx])
        return _extract_lines(filepath, start, end)

    # Top-level functions
    for func in getattr(parsed_file, "functions", []) or []:
        chunks.append(
            CodeChunk(
                file=filepath,
                symbol=func.name,
                symbol_type="function",
                start_line=func.start_line,
                end_line=func.end_line,
                code=get_lines(func.start_line, func.end_line),
                metadata={
                    "calls": getattr(func, "calls", []),
                    "docstring": getattr(func, "docstring", None),
                },
            )
        )

    # Classes
    for cls in getattr(parsed_file, "classes", []) or []:
        methods = getattr(cls, "methods", []) or []
        if methods:
            for method in methods:
                chunks.append(
                    CodeChunk(
                        file=filepath,
                        symbol=f"{cls.name}.{method.name}",
                        symbol_type="method",
                        start_line=method.start_line,
                        end_line=method.end_line,
                        code=get_lines(method.start_line, method.end_line),
                        metadata={
                            "class": cls.name,
                            "calls": getattr(method, "calls", []),
                            "docstring": getattr(method, "docstring", None),
                        },
                    )
                )
        else:
            # Whole-class chunk (e.g. dataclass with no explicit methods)
            meta: dict = {}
            docstring = getattr(cls, "docstring", None)
            if docstring:
                meta["docstring"] = docstring
            chunks.append(
                CodeChunk(
                    file=filepath,
                    symbol=cls.name,
                    symbol_type="class",
                    start_line=cls.start_line,
                    end_line=cls.end_line,
                    code=get_lines(cls.start_line, cls.end_line),
                    metadata=meta,
                )
            )

    return chunks


def chunk_to_dict(chunk: CodeChunk) -> dict:
    """Convert a CodeChunk to a plain dict."""
    d = {
        "file": chunk.file,
        "file_path": chunk.file,
        "symbol": chunk.symbol,
        "symbol_name": chunk.symbol,
        "type": chunk.symbol_type,
        "symbol_type": chunk.symbol_type,
        "start_line": chunk.start_line,
        "end_line": chunk.end_line,
        "code": chunk.code,
        "citation": chunk.citation(),
    }
    if chunk.chunk_id:
        d["chunk_id"] = chunk.chunk_id
    d.update(chunk.metadata)
    return d


