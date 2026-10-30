from typing import List, Optional, Set
from rank_bm25 import BM25Okapi
import json
import redis
import time
import random
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


def _normalize_chunk(c: dict) -> dict:
    """
    Normalizes chunk dict representation for Redis storage.
    Preserves source_id if present; leaves it absent/None for legacy records.
    """
    chunk_id = str(c.get("chunk_id", ""))
    text = c.get("text", "")
    item = {"chunk_id": chunk_id, "text": text}
    if c.get("source_id") is not None:
        item["source_id"] = str(c["source_id"])
    return item


def _merge_chunks(existing_chunks: List[dict], new_chunks: List[dict]) -> List[dict]:
    """
    Merges new_chunks into existing_chunks for a workspace index.

    Rules:
    1. Resolve duplicate incoming chunk IDs before deriving incoming_source_ids.
    2. Reject conflicting source_id ownership for the same chunk_id with a ValueError.
    3. For every source_id present in new_chunks, any existing chunks matching that source_id
       are removed (replacing the source's chunks upon re-ingestion).
    4. Any existing chunks whose chunk_id matches an incoming chunk_id are replaced.
    5. Existing chunks belonging to other sources (or legacy chunks without source_id)
       are preserved.
    """
    incoming_by_id: dict[str, dict] = {}

    for c in new_chunks:
        if not isinstance(c, dict):
            continue
        norm = _normalize_chunk(c)
        cid = norm["chunk_id"]
        if not cid:
            continue

        sid = norm.get("source_id")
        if cid in incoming_by_id:
            prior_sid = incoming_by_id[cid].get("source_id")
            if prior_sid is not None and sid is not None and prior_sid != sid:
                raise ValueError(
                    f"Conflicting source_id detected for incoming chunk_id '{cid}': '{prior_sid}' vs '{sid}'"
                )
        incoming_by_id[cid] = norm

    # Derive incoming sets after resolving duplicate incoming chunk IDs
    deduped_new = list(incoming_by_id.values())
    incoming_chunk_ids = set(incoming_by_id.keys())
    incoming_source_ids = {c["source_id"] for c in deduped_new if "source_id" in c}

    # Validate against existing chunks: reject conflicting source ownership
    for c in existing_chunks:
        if not isinstance(c, dict):
            continue
        cid = str(c.get("chunk_id", ""))
        if cid in incoming_by_id:
            existing_sid = c.get("source_id")
            incoming_sid = incoming_by_id[cid].get("source_id")
            if (
                existing_sid is not None
                and incoming_sid is not None
                and str(existing_sid) != str(incoming_sid)
            ):
                raise ValueError(
                    f"Conflicting source ownership for chunk_id '{cid}': "
                    f"existing source '{existing_sid}' vs incoming source '{incoming_sid}'"
                )

    # Filter existing chunks
    merged: List[dict] = []
    for c in existing_chunks:
        if not isinstance(c, dict):
            continue
        cid = str(c.get("chunk_id", ""))
        sid = str(c.get("source_id")) if c.get("source_id") is not None else None

        # Re-ingestion: remove prior chunks of the same source
        if sid is not None and sid in incoming_source_ids:
            continue
        # Deduplication: remove existing chunk if being updated with same chunk_id
        if cid in incoming_chunk_ids:
            continue

        merged.append(c)

    merged.extend(deduped_new)
    return merged


def save_index_to_redis(
    workspace_id: str,
    chunks: List[dict],
    client: Optional[redis.Redis] = None,
):
    """
    Saves chunk texts, chunk_ids, and source_ids to Redis for BM25 search.
    Preserves chunks from other sources in the workspace.
    Uses Redis WATCH/MULTI/EXEC for optimistic concurrency safety.
    Key: bm25:{workspace_id}
    """
    if not chunks:
        return

    should_close = False
    if client is None:
        client = get_redis_client()
        should_close = True

    try:
        key = f"bm25:{str(workspace_id)}"
        max_retries = 10

        for attempt in range(max_retries):
            pipe = client.pipeline()
            try:
                pipe.watch(key)
                raw = pipe.get(key)
                existing = []
                if raw:
                    try:
                        parsed = json.loads(raw)
                        if isinstance(parsed, list):
                            existing = parsed
                    except (json.JSONDecodeError, TypeError):
                        existing = []

                merged = _merge_chunks(existing, chunks)
                data_to_store = json.dumps(merged)

                pipe.multi()
                pipe.set(key, data_to_store, ex=86400)  # 24hr TTL
                pipe.execute()
                print(f"[sparse] Saved {len(merged)} chunks ({len(chunks)} incoming) to Redis BM25 index")
                return
            except redis.WatchError:
                if attempt == max_retries - 1:
                    print(f"[sparse] Failed to update BM25 index for workspace {workspace_id} after {max_retries} attempts due to concurrent updates")
                    raise
                time.sleep(random.uniform(0.01, 0.04) * (attempt + 1))
                continue
            finally:
                if hasattr(pipe, "close"):
                    pipe.close()
                elif hasattr(pipe, "reset"):
                    pipe.reset()
    finally:
        if should_close and hasattr(client, "close"):
            client.close()


def load_index_from_redis(
    workspace_id: str,
    client: Optional[redis.Redis] = None,
) -> List[dict]:
    """
    Loads chunk data from Redis for a workspace.
    """
    should_close = False
    if client is None:
        client = get_redis_client()
        should_close = True

    try:
        raw = client.get(f"bm25:{str(workspace_id)}")
        if not raw:
            return []
        try:
            data = json.loads(raw)
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, TypeError):
            return []
    finally:
        if should_close and hasattr(client, "close"):
            client.close()


def delete_source_from_redis(
    workspace_id: str,
    source_id: str,
    client: Optional[redis.Redis] = None,
):
    """
    Removes all chunks for a specific source from the workspace BM25 index.
    Uses Redis WATCH/MULTI/EXEC for atomic concurrency safety.
    """
    should_close = False
    if client is None:
        client = get_redis_client()
        should_close = True

    try:
        key = f"bm25:{str(workspace_id)}"
        target_sid = str(source_id)
        max_retries = 10

        for attempt in range(max_retries):
            pipe = client.pipeline()
            try:
                pipe.watch(key)
                raw = pipe.get(key)
                if not raw:
                    return
                try:
                    existing = json.loads(raw)
                    if not isinstance(existing, list):
                        return
                except (json.JSONDecodeError, TypeError):
                    return

                remaining = [
                    c for c in existing
                    if isinstance(c, dict) and str(c.get("source_id")) != target_sid
                ]

                pipe.multi()
                if remaining:
                    pipe.set(key, json.dumps(remaining), ex=86400)
                else:
                    pipe.delete(key)
                pipe.execute()
                print(f"[sparse] Removed source {source_id} from BM25 index (remaining: {len(remaining)})")
                return
            except redis.WatchError:
                if attempt == max_retries - 1:
                    raise
                time.sleep(random.uniform(0.01, 0.04) * (attempt + 1))
                continue
            finally:
                if hasattr(pipe, "close"):
                    pipe.close()
                elif hasattr(pipe, "reset"):
                    pipe.reset()
    finally:
        if should_close and hasattr(client, "close"):
            client.close()


async def sparse_search(
    query: str,
    workspace_id: str,
    top_k: int = 20,
    source_ids: Optional[List[str]] = None,
    client: Optional[redis.Redis] = None,
) -> List[dict]:
    """
    Performs BM25 keyword search over chunks stored in Redis.
    Returns list of scored chunks.
    Excludes non-matching chunks with zero query term overlap.
    """
    # Load chunks from Redis
    chunks = load_index_from_redis(workspace_id, client=client)

    if not chunks:
        print(f"[sparse] No BM25 index found for workspace {workspace_id}")
        return []

    # Filter by source_ids if provided
    if source_ids:
        target_sids = {str(sid) for sid in source_ids}
        # Only retain chunks with a matching source_id; legacy chunks without source_id are excluded when filtering
        chunks = [
            c for c in chunks
            if isinstance(c, dict) and c.get("source_id") is not None and str(c["source_id"]) in target_sids
        ]

    if not chunks:
        return []

    tokenized_query = query.lower().split()
    if not tokenized_query:
        return []

    # Build BM25 index
    index = build_bm25_index(chunks)

    # Get scores
    scores = index.get_scores(tokenized_query)

    query_tokens = set(tokenized_query)
    scored_chunks = []
    for i in range(len(chunks)):
        chunk_text_tokens = set(chunks[i]["text"].lower().split())
        has_overlap = bool(query_tokens & chunk_text_tokens)
        score = float(scores[i])

        # Exclude chunks with zero lexical match.
        # For small-corpus edge cases (e.g. N=1, N=2) where RSJ IDF is non-positive,
        # grant a positive epsilon score if there is actual query token overlap.
        if has_overlap:
            adj_score = max(0.001, score) if score <= 0.0 else score
            scored_chunks.append({
                "chunk_id": chunks[i]["chunk_id"],
                "score": adj_score,
                "text": chunks[i]["text"],
                "source_id": chunks[i].get("source_id"),
            })
        elif score > 0.0:
            scored_chunks.append({
                "chunk_id": chunks[i]["chunk_id"],
                "score": score,
                "text": chunks[i]["text"],
                "source_id": chunks[i].get("source_id"),
            })

    scored_chunks.sort(key=lambda x: x["score"], reverse=True)
    top_chunks = scored_chunks[:top_k]

    print(f"[sparse] BM25 found {len(top_chunks)} results")
    return top_chunks
