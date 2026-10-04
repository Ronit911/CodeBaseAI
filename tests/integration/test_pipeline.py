"""
Integration test: full Review-1 pipeline (no external services).

Tests the end-to-end data flow:

    GitHub URL
        ↓ (skipped — we use a local fixture directory instead)
    AST Parser          (parser.ast_parser.parser)
        ↓
    Chunker             (parser.chunker.chunker)
        ↓
    Schema conversion   (app.schemas.code_chunk.CodeChunk)
        ↓
    Neo4j graph         (graph.neo4j.graph_builder.GraphBuilder)   ← mocked
        ↓
    Embedder            (retrieval.vector.embedder.Embedder)        ← mocked
        ↓
    VectorStore         (retrieval.vector.vector_store.VectorStore) ← mocked
        ↓
    BM25Index           (retrieval.bm25.bm25_index.BM25Index)

External services (Neo4j, Qdrant, sentence-transformers model) are mocked
so the test runs without any infrastructure dependencies.
"""

import tempfile
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Fixture — write a tiny Python repo into a temp directory
# ---------------------------------------------------------------------------

FIXTURE_CODE = {
    "auth.py": """
        import os
        from database import get_user

        class AuthService:
            def login(self, username, password):
                user = get_user(username)
                return self.authenticate(user, password)

            def authenticate(self, user, password):
                return user is not None
    """,
    "database.py": """
        def get_user(username):
            return {"name": username}

        def save_user(user):
            pass
    """,
}


@pytest.fixture()
def repo_dir(tmp_path: Path) -> Path:
    """Create a minimal fixture repository on disk."""
    for filename, code in FIXTURE_CODE.items():
        (tmp_path / filename).write_text(textwrap.dedent(code), encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# Phase 3: AST Parser
# ---------------------------------------------------------------------------

class TestASTParser:
    def test_discovers_functions(self, repo_dir):
        from parser.ast_parser.parser import parse_file

        result = parse_file(repo_dir / "database.py")
        names = {f.name for f in result.functions}
        assert "get_user" in names
        assert "save_user" in names

    def test_discovers_classes_and_methods(self, repo_dir):
        from parser.ast_parser.parser import parse_file

        result = parse_file(repo_dir / "auth.py")
        assert len(result.classes) == 1
        cls = result.classes[0]
        assert cls.name == "AuthService"
        method_names = {m.name for m in cls.methods}
        assert "login" in method_names
        assert "authenticate" in method_names

    def test_discovers_imports(self, repo_dir):
        from parser.ast_parser.parser import parse_file

        result = parse_file(repo_dir / "auth.py")
        assert "os" in result.imports
        assert "database" in result.imports

    def test_call_graph(self, repo_dir):
        from parser.ast_parser.parser import parse_file

        result = parse_file(repo_dir / "auth.py")
        cls = result.classes[0]
        login = next(m for m in cls.methods if m.name == "login")
        assert "get_user" in login.calls or "authenticate" in login.calls


# ---------------------------------------------------------------------------
# Phase 4: Chunker
# ---------------------------------------------------------------------------

class TestChunker:
    def test_produces_chunks_for_all_files(self, repo_dir):
        from parser.ast_parser.parser import parse_file
        from parser.chunker.chunker import chunk_parsed_file

        py_files = list(repo_dir.glob("*.py"))
        all_chunks = []
        for f in py_files:
            parsed = parse_file(f)
            all_chunks.extend(chunk_parsed_file(parsed))

        assert len(all_chunks) > 0

    def test_chunk_has_required_fields(self, repo_dir):
        from parser.ast_parser.parser import parse_file
        from parser.chunker.chunker import chunk_parsed_file

        parsed = parse_file(repo_dir / "database.py")
        chunks = chunk_parsed_file(parsed)

        for chunk in chunks:
            assert chunk.symbol, "symbol name must not be empty"
            assert chunk.code, "code must not be empty"
            assert chunk.start_line >= 1
            assert chunk.end_line >= chunk.start_line

    def test_method_chunks_include_class_prefix(self, repo_dir):
        from parser.ast_parser.parser import parse_file
        from parser.chunker.chunker import chunk_parsed_file

        parsed = parse_file(repo_dir / "auth.py")
        chunks = chunk_parsed_file(parsed)
        symbols = {c.symbol for c in chunks}
        assert "AuthService.login" in symbols


# ---------------------------------------------------------------------------
# Phase 3+4 → Schema conversion
# ---------------------------------------------------------------------------

class TestSchemaConversion:
    def test_convert_to_code_chunk_schema(self, repo_dir):
        from parser.ast_parser.parser import parse_file
        from parser.chunker.chunker import chunk_parsed_file
        from app.schemas.code_chunk import CodeChunk, SymbolType

        parsed = parse_file(repo_dir / "database.py")
        raw_chunks = chunk_parsed_file(parsed)

        schema_chunks = [
            CodeChunk(
                repository_id="test-repo-id",
                file_path=c.file,
                symbol_name=c.symbol,
                symbol_type=SymbolType(c.symbol_type),
                start_line=c.start_line,
                end_line=c.end_line,
                code=c.code,
                extra=c.metadata,
            )
            for c in raw_chunks
        ]

        for sc in schema_chunks:
            assert sc.chunk_id, "chunk_id must be auto-generated"
            assert sc.repository_id == "test-repo-id"
            assert sc.citation(), "citation() must return a non-empty string"


# ---------------------------------------------------------------------------
# Phase 5: Neo4j (mocked)
# ---------------------------------------------------------------------------

class TestGraphBuilder:
    def test_graph_builder_called_with_parsed_files(self, repo_dir):
        from parser.ast_parser.parser import parse_file

        parsed_files = [parse_file(f) for f in repo_dir.glob("*.py")]

        with patch("graph.neo4j.graph_builder.GraphDatabase") as mock_gdb:
            mock_session = MagicMock()
            mock_gdb.driver.return_value.session.return_value.__enter__.return_value = mock_session

            from graph.neo4j.graph_builder import GraphBuilder
            builder = GraphBuilder.__new__(GraphBuilder)
            builder.driver = mock_gdb.driver.return_value
            builder.build(parsed_files)

            # At least one write transaction should have been attempted
            assert mock_session.execute_write.call_count > 0


# ---------------------------------------------------------------------------
# Phase 6: Embedder + VectorStore (mocked)
# ---------------------------------------------------------------------------

class TestEmbedderAndVectorStore:
    def test_embedder_returns_one_vector_per_text(self):
        with patch("retrieval.vector.embedder.SentenceTransformer") as MockST:
            import numpy as np
            mock_model = MockST.return_value
            mock_model.encode.return_value = np.zeros((3, 384))

            from retrieval.vector.embedder import Embedder
            embedder = Embedder.__new__(Embedder)
            embedder.model = mock_model
            embedder.vector_size = 384

            texts = ["def foo(): pass", "class Bar: pass", "import os"]
            vectors = embedder.encode(texts)

            assert len(vectors) == 3
            assert len(vectors[0]) == 384

    def test_vector_store_upserts_correct_number_of_points(self, repo_dir):
        from parser.ast_parser.parser import parse_file
        from parser.chunker.chunker import chunk_parsed_file
        from app.schemas.code_chunk import CodeChunk, SymbolType

        parsed = parse_file(repo_dir / "database.py")
        raw_chunks = chunk_parsed_file(parsed)
        chunks = [
            CodeChunk(
                repository_id="test-repo",
                file_path=c.file,
                symbol_name=c.symbol,
                symbol_type=SymbolType(c.symbol_type),
                start_line=c.start_line,
                end_line=c.end_line,
                code=c.code,
            )
            for c in raw_chunks
        ]
        fake_vectors = [[0.0] * 384 for _ in chunks]

        with patch("retrieval.vector.vector_store.QdrantClient") as MockQdrant:
            mock_client = MockQdrant.return_value
            mock_client.get_collections.return_value.collections = []

            from retrieval.vector.vector_store import VectorStore
            store = VectorStore.__new__(VectorStore)
            store.client = mock_client

            store.upsert(chunks=chunks, vectors=fake_vectors, collection="test-repo")

            mock_client.upsert.assert_called_once()
            call_args = mock_client.upsert.call_args
            points = call_args.kwargs.get("points") or call_args.args[1]
            assert len(points) == len(chunks)


# ---------------------------------------------------------------------------
# Phase 7: BM25 Index
# ---------------------------------------------------------------------------

class TestBM25Index:
    def test_build_and_search(self, repo_dir, tmp_path, monkeypatch):
        from parser.ast_parser.parser import parse_file
        from parser.chunker.chunker import chunk_parsed_file
        from app.schemas.code_chunk import CodeChunk, SymbolType

        # Redirect index storage to a temp dir
        monkeypatch.setattr("retrieval.bm25.bm25_index.INDEX_DIR", tmp_path)

        parsed = parse_file(repo_dir / "database.py")
        raw_chunks = chunk_parsed_file(parsed)
        chunks = [
            CodeChunk(
                repository_id="bm25-test",
                file_path=c.file,
                symbol_name=c.symbol,
                symbol_type=SymbolType(c.symbol_type),
                start_line=c.start_line,
                end_line=c.end_line,
                code=c.code,
            )
            for c in raw_chunks
        ]

        from retrieval.bm25.bm25_index import BM25Index
        idx = BM25Index()
        idx.build(chunks=chunks, index_name="bm25-test")

        results = idx.search(query="get_user username", index_name="bm25-test", top_k=2)

        assert len(results) > 0
        top = results[0]
        assert "score" in top
        assert "symbol_name" in top
        assert "citation" in top
        assert top["symbol_name"] == "get_user"
