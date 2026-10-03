"""
BM25 Index — builds and searches a BM25 index over code chunks.
"""

import json
import logging
import pickle
from pathlib import Path
from typing import TYPE_CHECKING

from rank_bm25 import BM25Okapi

if TYPE_CHECKING:
    from parser.chunker.chunker import CodeChunk

logger = logging.getLogger(__name__)

INDEX_DIR = Path("data/processed/bm25")


def _tokenize(text: str) -> list[str]:
    """Simple whitespace + identifier tokeniser."""
    import re
    return re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", text.lower())


class BM25Index:
    def __init__(self):
        INDEX_DIR.mkdir(parents=True, exist_ok=True)

    def build(self, chunks: list["CodeChunk"], index_name: str) -> None:
        corpus = [_tokenize(c.code) for c in chunks]
        bm25 = BM25Okapi(corpus)

        index_path = INDEX_DIR / f"{index_name}.pkl"
        meta_path = INDEX_DIR / f"{index_name}_meta.json"

        with open(index_path, "wb") as f:
            pickle.dump(bm25, f)

        meta = [
            {
                "file": c.file,
                "symbol": c.symbol,
                "type": c.symbol_type,
                "start_line": c.start_line,
                "end_line": c.end_line,
            }
            for c in chunks
        ]
        with open(meta_path, "w") as f:
            json.dump(meta, f)

        logger.info(f"BM25 index '{index_name}' built with {len(chunks)} chunks")

    def search(self, query: str, index_name: str, top_k: int = 5) -> list[dict]:
        index_path = INDEX_DIR / f"{index_name}.pkl"
        meta_path = INDEX_DIR / f"{index_name}_meta.json"

        with open(index_path, "rb") as f:
            bm25: BM25Okapi = pickle.load(f)
        with open(meta_path) as f:
            meta: list[dict] = json.load(f)

        tokens = _tokenize(query)
        scores = bm25.get_scores(tokens)
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

        return [{"score": float(scores[i]), **meta[i]} for i in top_indices]
