from typing import List, Optional
from uuid import UUID
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchAny
from app.config import settings
from app.services.ingestion.embedder import embed_query


_client = None


def get_qdrant_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY or None,
        )
    return _client


async def dense_search(
    query: str,
    workspace_id: str,
    top_k: int = 20,
    source_ids: Optional[List[str]] = None,
    is_code: bool = False,
) -> List[dict]:
    """
    Performs dense vector search in Qdrant.
    Supports optional source_ids filter for scoped retrieval.
    Returns list of scored chunks.
    """
    client = get_qdrant_client()
    collection = settings.QDRANT_COLLECTION

    # Embed the query
    query_vector = embed_query(query, is_code=is_code)

    # Build filter
    must_conditions = [
        FieldCondition(
            key="workspace_id",
            match=MatchAny(any=[workspace_id]),
        )
    ]

    if source_ids:
        must_conditions.append(
            FieldCondition(
                key="source_id",
                match=MatchAny(any=source_ids),
            )
        )

    search_filter = Filter(must=must_conditions)

    # Search
    results = client.search(
        collection_name=collection,
        query_vector=query_vector,
        query_filter=search_filter,
        limit=top_k,
        with_payload=True,
    )

    chunks = []
    for result in results:
        chunks.append({
            "chunk_id": result.id,
            "score": result.score,
            "text": result.payload.get("text", ""),
            "parent_id": result.payload.get("parent_id"),
            "source_id": result.payload.get("source_id"),
            "metadata": result.payload,
        })

    print(f"[dense] Found {len(chunks)} results for query")
    return chunks