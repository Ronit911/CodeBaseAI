"""
Embedder — generates sentence-transformer embeddings for code chunks
and upserts them into a Qdrant collection.
"""

import logging
import uuid
from typing import TYPE_CHECKING

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer

if TYPE_CHECKING:
    from parser.chunker.chunker import CodeChunk

logger = logging.getLogger(__name__)

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
VECTOR_SIZE = 384


class Embedder:
    def __init__(self, host: str = "localhost", port: int = 6333):
        self.client = QdrantClient(host=host, port=port)
        self.model = SentenceTransformer(MODEL_NAME)

    def _ensure_collection(self, collection: str) -> None:
        existing = [c.name for c in self.client.get_collections().collections]
        if collection not in existing:
            self.client.create_collection(
                collection_name=collection,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )
            logger.info(f"Created Qdrant collection: {collection}")

    def index(self, chunks: list["CodeChunk"], collection: str) -> None:
        self._ensure_collection(collection)
        texts = [chunk.code for chunk in chunks]
        vectors = self.model.encode(texts, show_progress_bar=True).tolist()

        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vec,
                payload={
                    "file": chunk.file,
                    "symbol": chunk.symbol,
                    "type": chunk.symbol_type,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                },
            )
            for chunk, vec in zip(chunks, vectors)
        ]
        self.client.upsert(collection_name=collection, points=points)
        logger.info(f"Indexed {len(points)} chunks into Qdrant collection '{collection}'")

    def search(self, query: str, collection: str, top_k: int = 5) -> list[dict]:
        query_vec = self.model.encode(query).tolist()
        results = self.client.search(
            collection_name=collection,
            query_vector=query_vec,
            limit=top_k,
        )
        return [{"score": r.score, **r.payload} for r in results]
