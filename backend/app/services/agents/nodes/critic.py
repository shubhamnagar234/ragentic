from app.services.agents.state import RagenticState
from app.services.eval.ragas_eval import evaluate_response, should_retry
from app.services.retrieval.confidence import compute_confidence
from datetime import datetime


async def critic_node(state: RagenticState) -> RagenticState:
    """
    Evaluates retrieved context quality using RAGAS.
    Computes confidence score.
    If faithfulness < 0.7 and retry_count < 2 → triggers retry.
    Updates state with eval scores and confidence level.
    """
    print(f"[critic] Evaluating retrieval quality...")

    reranked_chunks = state.get("reranked_chunks", [])
    query = state["query"]

    # Extract context texts
    contexts = [c["text"] for c in reranked_chunks]

    # Compute confidence from reranker scores
    confidence_level, confidence_score = compute_confidence(reranked_chunks)

    # Run RAGAS evaluation if we have context
    eval_result = None
    faithfulness = None
    context_precision = None
    answer_relevance = None

    if contexts:
        # Use a placeholder answer for context evaluation
        # Real answer evaluation happens after generation
        eval_result = await evaluate_response(
            query=query,
            answer="placeholder",
            contexts=contexts,
        )

        if eval_result:
            faithfulness = eval_result.faithfulness
            context_precision = eval_result.context_precision
            answer_relevance = eval_result.answer_relevance

    # Determine if retry is needed
    needs_retry = should_retry(eval_result) and state.get("retry_count", 0) < 2

    # Log timeline event
    event = {
        "agent": "critic",
        "status": "retrying" if needs_retry else "completed",
        "message": (
            f"Faithfulness: {faithfulness:.2f} → {'retry triggered' if needs_retry else 'passed'}"
            if faithfulness is not None
            else f"Confidence: {confidence_level}"
        ),
        "timestamp": datetime.utcnow().isoformat(),
        "metadata": {
            "faithfulness": faithfulness,
            "confidence_level": confidence_level,
            "confidence_score": confidence_score,
            "needs_retry": needs_retry,
        },
    }

    print(
        f"[critic] Confidence: {confidence_level}, Faithfulness: {faithfulness}, Retry: {needs_retry}"
    )

    return {
        **state,
        "faithfulness_score": faithfulness,
        "context_precision": context_precision,
        "answer_relevance": answer_relevance,
        "confidence_level": confidence_level,
        "timeline_events": state.get("timeline_events", []) + [event],
    }
