from typing import List


def reciprocal_rank_fusion(
    dense_results: List[dict],
    sparse_results: List[dict],
    k: int = 60,
    dense_weight: float = 0.6,
    sparse_weight: float = 0.4,
) -> List[dict]:
    """
    Reciprocal Rank Fusion (RRF) merges dense and sparse ranked lists.
    RRF score = dense_weight * (1 / (k + rank)) + sparse_weight * (1 / (k + rank))
    Returns unified ranked list of chunks.
    """
    scores = {}
    chunk_data = {}

    # Score dense results
    for rank, chunk in enumerate(dense_results):
        chunk_id = str(chunk["chunk_id"])
        rrf_score = dense_weight * (1 / (k + rank + 1))
        scores[chunk_id] = scores.get(chunk_id, 0) + rrf_score
        chunk_data[chunk_id] = chunk

    # Score sparse results
    for rank, chunk in enumerate(sparse_results):
        chunk_id = str(chunk["chunk_id"])
        rrf_score = sparse_weight * (1 / (k + rank + 1))
        scores[chunk_id] = scores.get(chunk_id, 0) + rrf_score
        if chunk_id not in chunk_data:
            chunk_data[chunk_id] = chunk

    # Sort by fused score
    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

    fused = []
    for chunk_id in sorted_ids:
        chunk = chunk_data[chunk_id].copy()
        chunk["rrf_score"] = scores[chunk_id]
        fused.append(chunk)

    print(
        f"[fusion] RRF merged {len(dense_results)} dense + {len(sparse_results)} sparse → {len(fused)} results"
    )
    return fused
