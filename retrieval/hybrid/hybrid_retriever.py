"""
Hybrid Retrieval — placeholder for Review 2.

Will combine:
  1. Vector search (Qdrant)
  2. BM25 search
  3. Graph traversal (Neo4j)

and apply a reranker before returning final results.
"""


class HybridRetriever:
    """Placeholder — implement in Review 2."""

    def search(self, query: str, repo_id: str, top_k: int = 10) -> list[dict]:
        raise NotImplementedError("Hybrid retrieval is implemented in Review 2")
