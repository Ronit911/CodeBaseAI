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


def _extract_lines(filepath: str, start: int, end: int) -> str:
    """Read the raw source lines for a given line range."""
    try:
        lines = Path(filepath).read_text(encoding="utf-8", errors="replace").splitlines()
        start_idx = max(0, start - 1)
        return "\n".join(lines[start_idx : end])
    except Exception:
        return ""


def chunk_parsed_file(parsed_file: ParsedFile) -> list[CodeChunk]:
    """
    Turn a ParsedFile into a list of CodeChunks.

    Strategy:
      - Each top-level function → 1 chunk
      - Each class method      → 1 chunk
      - Classes with no methods (data classes, etc.) → 1 chunk for the whole class
    """
    chunks: list[CodeChunk] = []
    filepath = parsed_file.file

    # Top-level functions
    for func in parsed_file.functions:
        chunks.append(
            CodeChunk(
                file=filepath,
                symbol=func.name,
                symbol_type="function",
                start_line=func.start_line,
                end_line=func.end_line,
                code=_extract_lines(filepath, func.start_line, func.end_line),
                metadata={"calls": func.calls, "docstring": func.docstring},
            )
        )

    # Classes
    for cls in parsed_file.classes:
        if cls.methods:
            for method in cls.methods:
                chunks.append(
                    CodeChunk(
                        file=filepath,
                        symbol=f"{cls.name}.{method.name}",
                        symbol_type="method",
                        start_line=method.start_line,
                        end_line=method.end_line,
                        code=_extract_lines(filepath, method.start_line, method.end_line),
                        metadata={
                            "class": cls.name,
                            "calls": method.calls,
                            "docstring": method.docstring,
                        },
                    )
                )
        else:
            # Whole-class chunk (e.g. dataclass with no explicit methods)
            chunks.append(
                CodeChunk(
                    file=filepath,
                    symbol=cls.name,
                    symbol_type="class",
                    start_line=cls.start_line,
                    end_line=cls.end_line,
                    code=_extract_lines(filepath, cls.start_line, cls.end_line),
                    metadata={},
                )
            )

    return chunks


def chunk_to_dict(chunk: CodeChunk) -> dict:
    """Convert a CodeChunk to a plain dict."""
    return {
        "file": chunk.file,
        "symbol": chunk.symbol,
        "type": chunk.symbol_type,
        "start_line": chunk.start_line,
        "end_line": chunk.end_line,
        "code": chunk.code,
        **chunk.metadata,
    }

