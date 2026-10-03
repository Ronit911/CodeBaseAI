import os
import logging
from pathlib import Path

import git
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.repository import Repository, RepoStatus

logger = logging.getLogger(__name__)


class IngestionService:
    """
    Orchestrates the full Review-1 pipeline:
      1. Clone repository
      2. Identify Python files
      3. AST parse each file
      4. Chunk code
      5. Build Neo4j graph
      6. Generate + store embeddings (Qdrant)
      7. Build BM25 index
    """

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Step 0 – Record creation
    # ------------------------------------------------------------------

    def create_repo_record(self, github_url: str) -> Repository:
        name = github_url.rstrip("/").split("/")[-1]
        repo = Repository(github_url=github_url, name=name)
        self.db.add(repo)
        self.db.commit()
        self.db.refresh(repo)
        return repo

    # ------------------------------------------------------------------
    # Step 1 – Clone
    # ------------------------------------------------------------------

    def clone_repo(self, repo: Repository) -> Path:
        clone_dir = Path(settings.REPO_CLONE_DIR) / repo.id
        clone_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Cloning {repo.github_url} → {clone_dir}")
        git.Repo.clone_from(repo.github_url, clone_dir)
        return clone_dir

    # ------------------------------------------------------------------
    # Step 2 – Discover Python files
    # ------------------------------------------------------------------

    IGNORE_DIRS = {".git", "__pycache__", "node_modules", "venv", ".venv", "env", ".env", "dist", "build"}

    def discover_python_files(self, root: Path) -> list[Path]:
        files = []
        for path in root.rglob("*.py"):
            if not any(part in self.IGNORE_DIRS for part in path.parts):
                files.append(path)
        logger.info(f"Found {len(files)} Python files")
        return files

    # ------------------------------------------------------------------
    # Pipeline entry point
    # ------------------------------------------------------------------

    def run_pipeline(self, repo_id: str) -> None:
        repo = self.db.query(Repository).filter(Repository.id == repo_id).first()
        if not repo:
            logger.error(f"Repo {repo_id} not found")
            return

        try:
            self._update_status(repo, RepoStatus.CLONING)
            clone_dir = self.clone_repo(repo)
            repo.local_path = str(clone_dir)
            self.db.commit()

            self._update_status(repo, RepoStatus.PARSING)
            py_files = self.discover_python_files(clone_dir)

            # Phase 3 — AST parse (delegated to parser module)
            from parser.ast_parser.parser import parse_file
            parsed = [parse_file(f) for f in py_files]

            # Phase 4 — Chunk
            from parser.chunker.chunker import chunk_parsed_file
            chunks = []
            for parsed_file in parsed:
                chunks.extend(chunk_parsed_file(parsed_file))

            self._update_status(repo, RepoStatus.INDEXING)

            # Phase 5 — Neo4j graph
            from graph.neo4j.graph_builder import GraphBuilder
            GraphBuilder().build(parsed)

            # Phase 6 — Embeddings → Qdrant
            from retrieval.vector.embedder import Embedder
            Embedder().index(chunks, collection=repo_id)

            # Phase 7 — BM25 index
            from retrieval.bm25.bm25_index import BM25Index
            BM25Index().build(chunks, index_name=repo_id)

            self._update_status(repo, RepoStatus.DONE)
            logger.info(f"Pipeline complete for repo {repo_id}")

        except Exception as exc:
            logger.exception(f"Pipeline failed for repo {repo_id}: {exc}")
            self._update_status(repo, RepoStatus.ERROR)

    def _update_status(self, repo: Repository, status: RepoStatus) -> None:
        repo.status = status
        self.db.commit()
