"""
IngestionService — pure orchestrator for the Review-1 pipeline.

Responsibility: coordinate each phase in order and update the repo
status in the database.  Implementation details live in the dedicated
modules below; this file contains NO parsing, embedding, or indexing
logic of its own.

Pipeline phases
---------------
1. Clone       → GitPython                          (internal helper)
2. Discover    → file-system walk                   (internal helper)
3. AST parse   → parser.ast_parser.parser
4. Chunk       → parser.chunker.chunker
5. Graph       → graph.neo4j.graph_builder
6. Embed       → retrieval.vector.embedder  +
                 retrieval.vector.vector_store
7. BM25        → retrieval.bm25.bm25_index
"""

import logging
from pathlib import Path

import git
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.repository import Repository, RepoStatus
from app.schemas.code_chunk import CodeChunk, SymbolType

logger = logging.getLogger(__name__)

# Directories to skip during file discovery
_IGNORE_DIRS: frozenset[str] = frozenset({
    ".git", "__pycache__", "node_modules",
    "venv", ".venv", "env", "dist", "build",
})


class IngestionService:
    """Drives all seven pipeline phases for a single repository."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Public: record creation (called by the API route before the task)
    # ------------------------------------------------------------------

    def create_repo_record(self, github_url: str) -> Repository:
        name = github_url.rstrip("/").split("/")[-1]
        repo = Repository(github_url=github_url, name=name)
        self.db.add(repo)
        self.db.commit()
        self.db.refresh(repo)
        return repo

    # ------------------------------------------------------------------
    # Public: pipeline entry-point (run as a background task)
    # ------------------------------------------------------------------

    def run_pipeline(self, repo_id: str) -> None:
        repo = self.db.query(Repository).filter(Repository.id == repo_id).first()
        if not repo:
            logger.error("Repo %s not found in database", repo_id)
            return

        try:
            # ── Phase 1 & 2: clone + discover ────────────────────────
            self._set_status(repo, RepoStatus.CLONING)
            clone_dir = self._clone(repo)
            repo.local_path = str(clone_dir)
            self.db.commit()

            self._set_status(repo, RepoStatus.PARSING)
            py_files = self._discover_python_files(clone_dir)

            # ── Phase 3: AST parse ───────────────────────────────────
            from parser.ast_parser.parser import parse_file
            parsed_files = [parse_file(f) for f in py_files]
            logger.info("Parsed %d files for repo %s", len(parsed_files), repo_id)

            # ── Phase 4: chunk ───────────────────────────────────────
            from parser.chunker.chunker import chunk_parsed_file, CodeChunk as _LegacyChunk
            raw_chunks: list[_LegacyChunk] = []
            for pf in parsed_files:
                raw_chunks.extend(chunk_parsed_file(pf))

            # Convert legacy dataclass chunks → canonical CodeChunk schema
            chunks: list[CodeChunk] = [
                _to_schema_chunk(c, repo_id) for c in raw_chunks
            ]
            logger.info("Created %d chunks for repo %s", len(chunks), repo_id)

            self._set_status(repo, RepoStatus.INDEXING)

            # ── Phase 5: Neo4j graph ─────────────────────────────────
            from graph.neo4j.graph_builder import GraphBuilder
            GraphBuilder().build(parsed_files)
            logger.info("Graph built for repo %s", repo_id)

            # ── Phase 6: embeddings → Qdrant ─────────────────────────
            from retrieval.vector.embedder import Embedder
            from retrieval.vector.vector_store import VectorStore
            embedder = Embedder()
            store = VectorStore()
            vectors = embedder.encode([c.code for c in chunks])
            store.upsert(chunks=chunks, vectors=vectors, collection=repo_id)
            logger.info("Vectors stored for repo %s", repo_id)

            # ── Phase 7: BM25 index ──────────────────────────────────
            from retrieval.bm25.bm25_index import BM25Index
            BM25Index().build(chunks=chunks, index_name=repo_id)
            logger.info("BM25 index built for repo %s", repo_id)

            self._set_status(repo, RepoStatus.DONE)
            logger.info("Pipeline complete for repo %s", repo_id)

        except Exception:
            logger.exception("Pipeline failed for repo %s", repo_id)
            self._set_status(repo, RepoStatus.ERROR)

    # ------------------------------------------------------------------
    # Private helpers (infrastructure only — no domain logic)
    # ------------------------------------------------------------------

    def _clone(self, repo: Repository) -> Path:
        clone_dir = Path(settings.REPO_CLONE_DIR) / repo.id
        clone_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Cloning %s → %s", repo.github_url, clone_dir)
        git.Repo.clone_from(repo.github_url, clone_dir)
        return clone_dir

    def _discover_python_files(self, root: Path) -> list[Path]:
        files = [
            p for p in root.rglob("*.py")
            if not any(part in _IGNORE_DIRS for part in p.parts)
        ]
        logger.info("Discovered %d Python files", len(files))
        return files

    def _set_status(self, repo: Repository, status: RepoStatus) -> None:
        repo.status = status
        self.db.commit()


# ------------------------------------------------------------------
# Conversion helper (legacy chunker dataclass → canonical schema)
# ------------------------------------------------------------------

def _to_schema_chunk(chunk, repo_id: str) -> CodeChunk:
    """
    Convert a ``parser.chunker.chunker.CodeChunk`` dataclass to the
    canonical ``app.schemas.code_chunk.CodeChunk`` Pydantic model.
    """
    return CodeChunk(
        repository_id=repo_id,
        file_path=chunk.file,
        symbol_name=chunk.symbol,
        symbol_type=SymbolType(chunk.symbol_type),
        start_line=chunk.start_line,
        end_line=chunk.end_line,
        code=chunk.code,
        extra=chunk.metadata,
    )
