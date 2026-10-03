"""
Unit tests for the AST parser.
"""

import ast
import textwrap
from pathlib import Path
import tempfile

import pytest

from parser.ast_parser.parser import parse_file, ParsedFile


def _write_temp_py(code: str) -> Path:
    tmp = tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False, encoding="utf-8")
    tmp.write(textwrap.dedent(code))
    tmp.close()
    return Path(tmp.name)


def test_parse_functions():
    path = _write_temp_py("""
        def authenticate_user(username, password):
            return True

        def logout():
            pass
    """)
    result = parse_file(path)
    names = [f.name for f in result.functions]
    assert "authenticate_user" in names
    assert "logout" in names


def test_parse_classes():
    path = _write_temp_py("""
        class UserService:
            def get_user(self, user_id):
                pass

            def delete_user(self, user_id):
                pass
    """)
    result = parse_file(path)
    assert len(result.classes) == 1
    assert result.classes[0].name == "UserService"
    assert len(result.classes[0].methods) == 2


def test_parse_imports():
    path = _write_temp_py("""
        import os
        from pathlib import Path
        from app.models import User
    """)
    result = parse_file(path)
    assert "os" in result.imports
    assert "pathlib" in result.imports
    assert "app.models" in result.imports


def test_parse_calls():
    path = _write_temp_py("""
        def login():
            authenticate_user("admin", "secret")
    """)
    result = parse_file(path)
    assert "authenticate_user" in result.functions[0].calls


def test_parse_line_numbers():
    path = _write_temp_py("""
        def foo():
            pass

        def bar():
            pass
    """)
    result = parse_file(path)
    foo = next(f for f in result.functions if f.name == "foo")
    assert foo.start_line >= 1
    assert foo.end_line >= foo.start_line


def test_syntax_error_returns_empty():
    path = _write_temp_py("def broken(::")
    result = parse_file(path)
    assert isinstance(result, ParsedFile)
    assert result.functions == []
