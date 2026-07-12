from app.services.agents.state import RagenticState
from app.services.llm.client import get_llm_response
from app.services.retrieval.confidence import (
    get_confidence_prompt_instruction,
    ConfidenceLevel,
)
from app.services.eval.ragas_eval import evaluate_response
from datetime import datetime


async def responder_node(state: RagenticState) -> RagenticState:
    """
    Generates the final answer using retrieved context.
    Uses confidence level to frame the response appropriately.
    Runs LLM-based evaluation on the real answer (faithfulness, precision, relevance).
    Updates state with final_answer, sources_used, and eval scores.
    """
    print(f"[responder] Generating final answer...")

    query = state["query"]
    reranked_chunks = state.get("reranked_chunks", [])
    confidence_level = state.get("confidence_level", "MEDIUM")
    conversation_summary = state.get("conversation_summary", "")
    recent_turns = state.get("recent_turns", [])

    # Build context from reranked chunks
    context_parts = []
    sources_used = []

    for i, chunk in enumerate(reranked_chunks):
        context_parts.append(f"[Source {i+1}]: {chunk['text']}")
        sources_used.append(
            {
                "chunk_id": str(chunk.get("chunk_id", "")),
                "score": chunk.get("reranker_score", 0.0),
                "text_preview": chunk["text"][:150] + "...",
                "full_text": chunk.get("text", ""),
                "source_id": str(chunk.get("source_id", "")),
            }
        )

    context = "\n\n".join(context_parts)

    # Build conversation history for prompt
    history = ""
    if conversation_summary:
        history += f"Previous conversation summary:\n{conversation_summary}\n\n"
    if recent_turns:
        history += "Recent conversation:\n"
        for turn in recent_turns:
            history += f"{turn['role'].upper()}: {turn['content']}\n"
        history += "\n"

    # Get confidence instruction
    confidence_instruction = get_confidence_prompt_instruction(
        ConfidenceLevel(confidence_level)
    )

    # Build system prompt
    system_prompt = f"""You are RAGENTIC, an intelligent knowledge workspace assistant.
You answer questions based strictly on the provided context from the user's documents.

{confidence_instruction}

Always cite which source you used by referencing [Source N] in your answer.
Be concise, accurate, and helpful."""

    # Build user prompt
    user_prompt = f"""{history}Context:
{context}

Question: {query}

Answer:"""

    # Initialise eval scores
    faithfulness_score = None
    context_precision_score = None
    answer_relevance_score = None

    try:
        answer = await get_llm_response(
            prompt=user_prompt,
            system_prompt=system_prompt,
            max_tokens=1500,
        )

        # ── Run evaluation on the real answer ───────────────────────────────
        contexts = [c["text"] for c in reranked_chunks]
        eval_result = await evaluate_response(
            query=query,
            answer=answer,
            contexts=contexts,
        )
        if eval_result:
            faithfulness_score = eval_result.faithfulness
            context_precision_score = eval_result.context_precision
            answer_relevance_score = eval_result.answer_relevance
        # ────────────────────────────────────────────────────────────────────

        event = {
            "agent": "responder",
            "status": "completed",
            "message": f"Response generated using {len(sources_used)} sources",
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": {
                "sources_count": len(sources_used),
                "confidence_level": confidence_level,
                "faithfulness": faithfulness_score,
                "context_precision": context_precision_score,
                "answer_relevance": answer_relevance_score,
            },
        }

        print(f"[responder] Answer generated successfully")

        return {
            **state,
            "final_answer": answer,
            "sources_used": sources_used,
            "faithfulness_score": faithfulness_score,
            "context_precision": context_precision_score,
            "answer_relevance": answer_relevance_score,
            "timeline_events": state.get("timeline_events", []) + [event],
        }

    except Exception as e:
        print(f"[responder] Generation failed: {e}")

        return {
            **state,
            "final_answer": f"I encountered an error generating a response: {str(e)}",
            "sources_used": [],
            "faithfulness_score": None,
            "context_precision": None,
            "answer_relevance": None,
        }
