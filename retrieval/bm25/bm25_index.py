"""
BM25 Index — builds and searches a BM25 index over canonical CodeChunk objects.

Accepts ``app.schemas.code_chunk.CodeChunk`` (the shared schema) so it is
consistent with the rest of the pipeline.
"""

import json
import logging
import pickle
import re
from pathlib import Path

from rank_bm25 import BM25Okapi

from app.schemas.code_chunk import CodeChunk

logger = logging.getLogger(__name__)

INDEX_DIR = Path("data/processed/bm25")


def _tokenize(text: str) -> list[str]:
    """Simple identifier-aware tokeniser for source code."""
    return re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", text.lower())


class BM25Index:
    """Builds and queries a BM25Okapi index persisted to disk."""

    def __init__(self) -> None:
        INDEX_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def build(self, chunks: list[CodeChunk], index_name: str) -> None:
        """
        Build a BM25 index from a list of ``CodeChunk`` objects and
        persist both the index and its metadata to disk.

        Parameters
        ----------
        chunks:
            Canonical CodeChunk objects produced by the chunker.
        index_name:
            Typically the repository ID (used as a filename stem).
        """
        corpus = [_tokenize(c.code) for c in chunks]
        bm25 = BM25Okapi(corpus)

        index_path = INDEX_DIR / f"{index_name}.pkl"
        meta_path = INDEX_DIR / f"{index_name}_meta.json"

        with open(index_path, "wb") as fh:
            pickle.dump(bm25, fh)

        # Persist the metadata needed to reconstruct citation info
        meta = [
            {
                "chunk_id": c.chunk_id,
                "repository_id": c.repository_id,
                "file_path": c.file_path,
                "symbol_name": c.symbol_name,
                "symbol_type": c.symbol_type,
                "start_line": c.start_line,
                "end_line": c.end_line,
                "citation": c.citation(),
            }
            for c in chunks
        ]
        with open(meta_path, "w", encoding="utf-8") as fh:
            json.dump(meta, fh, indent=2)

        logger.info("BM25 index '%s' built with %d chunks", index_name, len(chunks))

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def search(self, query: str, index_name: str, top_k: int = 5) -> list[dict]:
        """
        Search the BM25 index and return the top-k results.

        Returns a list of metadata dicts augmented with a ``score`` field.
        """
        index_path = INDEX_DIR / f"{index_name}.pkl"
        meta_path = INDEX_DIR / f"{index_name}_meta.json"

        with open(index_path, "rb") as fh:
            bm25: BM25Okapi = pickle.load(fh)
        with open(meta_path, encoding="utf-8") as fh:
            meta: list[dict] = json.load(fh)

        tokens = _tokenize(query)
        scores = bm25.get_scores(tokens)
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

        return [{"score": float(scores[i]), **meta[i]} for i in top_indices]
