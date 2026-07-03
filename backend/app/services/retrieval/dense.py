from typing import List, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchAny, MatchValue
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
    client = get_qdrant_client()
    collection = settings.QDRANT_COLLECTION

    # Embed the query
    query_vector = embed_query(query, is_code=is_code)

    # Build filter conditions
    must_conditions = [
        FieldCondition(
            key="workspace_id",
            match=MatchValue(value=workspace_id),
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

    # Use query_points (qdrant-client >= 1.7)
    response = client.query_points(
        collection_name=collection,
        query=query_vector,
        query_filter=search_filter,
        limit=top_k,
        with_payload=True,
    )

    chunks = []
    for result in response.points:
        chunks.append(
            {
                "chunk_id": result.id,
                "score": result.score,
                "text": result.payload.get("text", ""),
                "parent_id": result.payload.get("parent_id"),
                "source_id": result.payload.get("source_id"),
                "metadata": result.payload,
            }
        )

    print(f"[dense] Found {len(chunks)} results for query")
    return chunks
