"""
VectorStore — manages the Qdrant collection for a repository.

Responsibility: vector + metadata → Qdrant ONLY.
Generating embedding vectors is handled by ``embedder.Embedder``.
"""

import logging
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from app.schemas.code_chunk import CodeChunk

logger = logging.getLogger(__name__)

VECTOR_SIZE = 384   # must match the model used in embedder.py


class VectorStore:
    """
    Thin wrapper around ``QdrantClient`` that speaks in terms of
    ``CodeChunk`` objects rather than raw Qdrant primitives.
    """

    def __init__(self, host: str = "localhost", port: int = 6333) -> None:
        self.client = QdrantClient(host=host, port=port)

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def ensure_collection(self, collection: str) -> None:
        """Create the Qdrant collection if it does not already exist."""
        existing = {c.name for c in self.client.get_collections().collections}
        if collection not in existing:
            self.client.create_collection(
                collection_name=collection,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )
            logger.info("Created Qdrant collection: %s", collection)

    def upsert(
        self,
        chunks: list[CodeChunk],
        vectors: list[list[float]],
        collection: str,
    ) -> None:
        """
        Upsert vectors together with their chunk metadata into Qdrant.

        Parameters
        ----------
        chunks:
            Canonical ``CodeChunk`` objects (provides metadata / payload).
        vectors:
            Pre-computed float vectors from ``Embedder.encode``.
            Must be the same length and order as ``chunks``.
        collection:
            Qdrant collection name (typically the repository ID).
        """
        if len(chunks) != len(vectors):
            raise ValueError(
                f"chunks ({len(chunks)}) and vectors ({len(vectors)}) must have the same length"
            )

        self.ensure_collection(collection)

        points = [
            PointStruct(
                id=chunk.chunk_id,
                vector=vector,
                payload={
                    "chunk_id": chunk.chunk_id,
                    "repository_id": chunk.repository_id,
                    "file_path": chunk.file_path,
                    "symbol_name": chunk.symbol_name,
                    "symbol_type": chunk.symbol_type,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "citation": chunk.citation(),
                },
            )
            for chunk, vector in zip(chunks, vectors)
        ]

        self.client.upsert(collection_name=collection, points=points)
        logger.info("Upserted %d vectors into Qdrant collection '%s'", len(points), collection)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def search(
        self,
        query_vector: list[float],
        collection: str,
        top_k: int = 5,
    ) -> list[dict]:
        """
        Search for the ``top_k`` most similar vectors.

        Returns a list of payload dicts augmented with a ``score`` field.
        """
        results = self.client.search(
            collection_name=collection,
            query_vector=query_vector,
            limit=top_k,
        )
        return [{"score": r.score, **r.payload} for r in results]
