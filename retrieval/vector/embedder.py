"""
Embedder — converts raw code strings into embedding vectors.

Responsibility: text → vector ONLY.
Storing vectors into Qdrant is handled by ``vector_store.VectorStore``.
"""

import logging

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
VECTOR_SIZE = 384   # dimension for all-MiniLM-L6-v2


class Embedder:
    """
    Wraps a sentence-transformers model and exposes a single ``encode``
    method.  No Qdrant knowledge here.
    """

    def __init__(self, model_name: str = MODEL_NAME) -> None:
        logger.info("Loading embedding model: %s", model_name)
        self.model = SentenceTransformer(model_name)
        self.vector_size = VECTOR_SIZE

    def encode(self, texts: list[str], show_progress: bool = False) -> list[list[float]]:
        """
        Encode a list of text strings into embedding vectors.

        Parameters
        ----------
        texts:
            Raw code (or any text) to embed.
        show_progress:
            Show a tqdm progress bar (useful for large batches).

        Returns
        -------
        list of float vectors, one per input text.
        """
        if not texts:
            return []
        vectors = self.model.encode(texts, show_progress_bar=show_progress)
        return vectors.tolist()

    def encode_query(self, query: str) -> list[float]:
        """Encode a single query string (convenience wrapper)."""
        return self.model.encode(query).tolist()
