from app.services.agents.state import RagenticState
from app.services.retrieval.dense import dense_search
from app.services.retrieval.sparse import sparse_search
from app.services.retrieval.fusion import reciprocal_rank_fusion
from app.services.retrieval.reranker import rerank_chunks
from datetime import datetime


async def retriever_node(state: RagenticState) -> RagenticState:
    """
    Performs hybrid retrieval:
    1. Dense vector search
    2. BM25 sparse search
    3. RRF fusion
    4. Cross-encoder reranking
    Updates state with reranked_chunks.
    """
    print(f"[retriever] Running hybrid retrieval...")

    query = state["query"]
    workspace_id = state["workspace_id"]
    source_ids = state.get("source_ids")
    top_k = state.get("top_k", 20)
    vector_weight = state.get("vector_weight", 0.6)
    bm25_weight = state.get("bm25_weight", 0.4)
    is_code = state.get("query_type") == "code"

    # Dense search
    dense_chunks = await dense_search(
        query=query,
        workspace_id=workspace_id,
        top_k=top_k,
        source_ids=source_ids,
        is_code=is_code,
    )

    # Sparse search
    sparse_chunks = await sparse_search(
        query=query,
        workspace_id=workspace_id,
        top_k=top_k,
        source_ids=source_ids,
    )

    # RRF fusion
    fused_chunks = reciprocal_rank_fusion(
        dense_results=dense_chunks,
        sparse_results=sparse_chunks,
        dense_weight=vector_weight,
        sparse_weight=bm25_weight,
    )

    # Rerank top results
    reranked_chunks = rerank_chunks(
        query=query,
        chunks=fused_chunks[:20],
        top_k=5,
        threshold=0.3,
    )

    # Log timeline event
    event = {
        "agent": "retriever",
        "status": "completed",
        "message": (
            f"Retrieved {len(dense_chunks)} dense + "
            f"{len(sparse_chunks)} sparse → "
            f"{len(reranked_chunks)} selected after reranking"
        ),
        "timestamp": datetime.utcnow().isoformat(),
        "metadata": {
            "dense_count": len(dense_chunks),
            "sparse_count": len(sparse_chunks),
            "reranked_count": len(reranked_chunks),
        },
    }

    return {
        **state,
        "dense_chunks": dense_chunks,
        "sparse_chunks": sparse_chunks,
        "fused_chunks": fused_chunks,
        "reranked_chunks": reranked_chunks,
        "timeline_events": state.get("timeline_events", []) + [event],
    }
