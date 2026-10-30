import math
from typing import List, Optional
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
    threshold: Optional[float] = None,
    min_k: int = 3,
) -> List[dict]:
    """
    Re-scores chunks using a cross-encoder model.
    Cross-encoder jointly encodes query + chunk for more accurate relevance scoring.

    Parameters:
    - query: User query string.
    - chunks: List of candidate chunk dicts (each containing 'text').
    - top_k: Maximum number of candidates to return (default 5).
    - threshold: Optional score threshold in [0.0, 1.0]. If None (default), candidates are
                 ranked and sliced to top_k without hard threshold pruning.
    - min_k: Fallback minimum candidate count when threshold filtering is active (default 3).
             Prevents aggressive context starvation when few candidates cross threshold.

    Returns:
    List of up to top_k reranked chunks with 'reranker_score' added, sorted descending.
    """
    # Parameter validation
    if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k < 1:
        raise ValueError(f"top_k must be a positive integer >= 1, got {top_k}")
    if isinstance(min_k, bool) or not isinstance(min_k, int) or min_k < 1:
        raise ValueError(f"min_k must be a positive integer >= 1, got {min_k}")

    if threshold is not None:
        if isinstance(threshold, bool):
            raise ValueError(f"threshold must be a finite float in [0.0, 1.0], got {threshold}")
        try:
            t = float(threshold)
            if not (math.isfinite(t) and 0.0 <= t <= 1.0):
                raise ValueError(f"threshold must be a finite float in [0.0, 1.0], got {threshold}")
            threshold = t
        except (ValueError, TypeError):
            raise ValueError(f"threshold must be a finite float in [0.0, 1.0], got {threshold}")

    if not chunks:
        return []

    reranker = get_reranker()

    # Build query-chunk pairs
    pairs = [[query, chunk.get("text", "")] for chunk in chunks]

    # Score all pairs
    print(f"[reranker] Scoring {len(pairs)} chunks...")
    scores = reranker.predict(pairs)

    def sigmoid(x):
        return 1.0 / (1.0 + math.exp(-float(x)))

    # Add scores to chunks (preserving original metadata)
    scored_chunks = []
    for chunk, score in zip(chunks, scores):
        chunk_copy = chunk.copy()
        chunk_copy["reranker_score"] = sigmoid(float(score))
        scored_chunks.append(chunk_copy)

    # Sort by reranker score descending (sigmoid is strictly monotonic w.r.t. raw logits)
    scored_chunks.sort(key=lambda x: x["reranker_score"], reverse=True)

    # If no threshold is specified, return top_k reranked candidates directly
    if threshold is None:
        result = scored_chunks[:top_k]
        print(f"[reranker] Returning top {len(result)} reranked chunks (no threshold filter)")
        return result

    # When threshold is provided, filter candidates but guarantee at least effective_min candidates
    filtered = [c for c in scored_chunks if c["reranker_score"] >= threshold]
    effective_min = min(min_k, top_k, len(scored_chunks))

    if len(filtered) < effective_min:
        filtered = scored_chunks[:effective_min]
    else:
        filtered = filtered[:top_k]

    print(f"[reranker] {len(filtered)} chunks returned (threshold={threshold}, min_k={min_k})")
    return filtered
