from typing import List, Optional
from rank_bm25 import BM25Okapi
import json
import redis
from app.config import settings


def get_redis_client():
    return redis.from_url(settings.REDIS_URL)


def build_bm25_index(chunks: List[dict]) -> BM25Okapi:
    """
    Builds a BM25 index from a list of chunks.
    Each chunk must have 'text' and 'chunk_id' fields.
    """
    tokenized = [chunk["text"].lower().split() for chunk in chunks]
    return BM25Okapi(tokenized)


def save_index_to_redis(workspace_id: str, chunks: List[dict]):
    """
    Saves chunk texts and IDs to Redis for BM25 search.
    Key: bm25:{workspace_id}
    """
    client = get_redis_client()
    data = [{"chunk_id": c["chunk_id"], "text": c["text"]} for c in chunks]
    client.set(f"bm25:{workspace_id}", json.dumps(data), ex=86400)  # 24hr TTL
    print(f"[sparse] Saved {len(data)} chunks to Redis BM25 index")


def load_index_from_redis(workspace_id: str) -> List[dict]:
    """
    Loads chunk data from Redis for a workspace.
    """
    client = get_redis_client()
    raw = client.get(f"bm25:{workspace_id}")
    if not raw:
        return []
    return json.loads(raw)


async def sparse_search(
    query: str,
    workspace_id: str,
    top_k: int = 20,
    source_ids: Optional[List[str]] = None,
) -> List[dict]:
    """
    Performs BM25 keyword search over chunks stored in Redis.
    Returns list of scored chunks.
    """
    # Load chunks from Redis
    chunks = load_index_from_redis(workspace_id)

    if not chunks:
        print(f"[sparse] No BM25 index found for workspace {workspace_id}")
        return []

    # Filter by source_ids if provided
    if source_ids:
        chunks = [c for c in chunks if c.get("source_id") in source_ids]

    if not chunks:
        return []

    # Build BM25 index
    index = build_bm25_index(chunks)

    # Tokenize query
    tokenized_query = query.lower().split()

    # Get scores
    scores = index.get_scores(tokenized_query)

    # Sort and return top_k
    scored_chunks = [
        {
            "chunk_id": chunks[i]["chunk_id"],
            "score": float(scores[i]),
            "text": chunks[i]["text"],
            "source_id": chunks[i].get("source_id"),
        }
        for i in range(len(chunks))
    ]

    scored_chunks.sort(key=lambda x: x["score"], reverse=True)
    top_chunks = scored_chunks[:top_k]

    print(f"[sparse] BM25 found {len(top_chunks)} results")
    return top_chunks
