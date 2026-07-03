import math
from typing import List
from sentence_transformers import CrossEncoder
from app.config import settings

# Load reranker model once at module level
RERANKER_MODEL = settings.RERANKER_MODEL
_reranker = None


def get_reranker() -> CrossEncoder:
    global _reranker
    if _reranker is None:
        print(f"[reranker] Loading reranker model: {RERANKER_MODEL}")
        _reranker = CrossEncoder(RERANKER_MODEL)
    return _reranker


def rerank_chunks(
    query: str,
    chunks: List[dict],
    top_k: int = 5,
    threshold: float = 0.3,
) -> List[dict]:
    """
    Re-scores chunks using a cross-encoder model.
    Cross-encoder jointly encodes query + chunk for more accurate relevance scoring.
    Only returns chunks above the threshold score.
    Returns top_k reranked chunks with reranker_score added.
    """
    if not chunks:
        return []

    reranker = get_reranker()

    # Build query-chunk pairs
    pairs = [[query, chunk["text"]] for chunk in chunks]

    # Score all pairs
    print(f"[reranker] Scoring {len(pairs)} chunks...")
    scores = reranker.predict(pairs)

    def sigmoid(x):
        return 1 / (1 + math.exp(-x))

    # Add scores to chunks
    scored_chunks = []
    for chunk, score in zip(chunks, scores):
        chunk_copy = chunk.copy()
        chunk_copy["reranker_score"] = sigmoid(float(score))
        scored_chunks.append(chunk_copy)

    # Sort by reranker score
    scored_chunks.sort(key=lambda x: x["reranker_score"], reverse=True)

    # Filter by threshold and take top_k
    filtered = [c for c in scored_chunks if c["reranker_score"] >= threshold][:top_k]

    print(f"[reranker] {len(filtered)} chunks passed threshold {threshold}")
    return filtered
