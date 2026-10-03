"""
Unit tests for the code chunker.
"""

import textwrap
import tempfile
from pathlib import Path

from parser.ast_parser.parser import parse_file
from parser.chunker.chunker import chunk_parsed_file


def _write_temp_py(code: str) -> Path:
    tmp = tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False, encoding="utf-8")
    tmp.write(textwrap.dedent(code))
    tmp.close()
    return Path(tmp.name)


def test_function_produces_chunk():
    path = _write_temp_py("""
        def authenticate_user(username, password):
            return True
    """)
    parsed = parse_file(path)
    chunks = chunk_parsed_file(parsed)
    assert len(chunks) == 1
    assert chunks[0].symbol == "authenticate_user"
    assert chunks[0].symbol_type == "function"


def test_class_methods_produce_separate_chunks():
    path = _write_temp_py("""
        class AuthService:
            def login(self):
                pass

            def logout(self):
                pass
    """)
    parsed = parse_file(path)
    chunks = chunk_parsed_file(parsed)
    symbols = [c.symbol for c in chunks]
    assert "AuthService.login" in symbols
    assert "AuthService.logout" in symbols


def test_chunk_has_code():
    path = _write_temp_py("""
        def foo():
            return 42
    """)
    parsed = parse_file(path)
    chunks = chunk_parsed_file(parsed)
    assert "return 42" in chunks[0].code


def test_chunk_metadata_fields():
    path = _write_temp_py("""
        def bar():
            baz()
    """)
    parsed = parse_file(path)
    chunks = chunk_parsed_file(parsed)
    chunk = chunks[0]
    assert chunk.file == str(path)
    assert chunk.start_line >= 1
    assert chunk.end_line >= chunk.start_line
