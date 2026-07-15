from app.services.agents.state import RagenticState
from app.services.retrieval.confidence import compute_confidence
from datetime import datetime


async def critic_node(state: RagenticState) -> RagenticState:
    """
    Evaluates retrieved context quality via reranker-based confidence scoring.

    The critic decides whether to retry retrieval based on reranker scores
    before the LLM generates an answer. RAGAS metrics (faithfulness,
    answer_relevance) require a real answer and are computed in the responder
    node instead — running them here on a placeholder answer was meaningless.

    Updates state with confidence_level so the responder can frame its reply
    appropriately, and so the conditional edge can decide whether to rewrite.
    """
    print(f"[critic] Evaluating retrieval quality...")

    reranked_chunks = state.get("reranked_chunks", [])

    # Compute confidence from reranker scores (reliable pre-generation signal)
    confidence_level, confidence_score = compute_confidence(reranked_chunks)

    # Low-confidence with room for retries → signal the edge to rewrite
    retry_count = state.get("retry_count", 0)
    needs_retry = confidence_level == "LOW" and retry_count < 2

    # Log timeline event
    event = {
        "agent": "critic",
        "status": "retrying" if needs_retry else "completed",
        "message": (
            f"Confidence: {str(confidence_level).split('.')[-1]} (score: {confidence_score:.2f})"
            f"{' → retry triggered' if needs_retry else ' → proceeding to respond'}"
        ),
        "timestamp": datetime.utcnow().isoformat(),
        "metadata": {
            "confidence_level": confidence_level,
            "confidence_score": confidence_score,
            "needs_retry": needs_retry,
            "chunk_count": len(reranked_chunks),
        },
    }

    print(
        f"[critic] Confidence: {confidence_level} ({confidence_score:.2f}), "
        f"Retry: {needs_retry}"
    )

    return {
        **state,
        # faithfulness_score stays None here; set by responder after real eval
        "faithfulness_score": None,
        "context_precision": None,
        "answer_relevance": None,
        "confidence_level": confidence_level,
        "timeline_events": state.get("timeline_events", []) + [event],
    }
