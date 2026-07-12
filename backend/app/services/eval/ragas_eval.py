"""
Self-contained LLM-based RAG evaluation.

Replaces the ragas library dependency with prompts that call our own
get_llm_response (Gemini/Groq via litellm).  Produces three scores:

  faithfulness      — is the answer grounded in the retrieved context?
  context_precision — how relevant are the retrieved chunks to the query?
  answer_relevance  — does the answer address the question asked?

All scores are floats in [0, 1].
"""

from typing import List, Optional
from dataclasses import dataclass
import json


@dataclass
class EvalResult:
    faithfulness: float
    context_precision: float
    answer_relevance: float


async def evaluate_response(
    query: str,
    answer: str,
    contexts: List[str],
) -> Optional[EvalResult]:
    """
    Evaluates a RAG response using lightweight LLM-based scoring.
    Returns EvalResult with scores in [0, 1], or None if evaluation fails.
    """
    from app.services.llm.client import get_llm_response

    if not contexts or not answer or answer == "placeholder":
        return None

    # Truncate to keep costs low (first 3 contexts, max 400 chars each)
    ctx_preview = "\n---\n".join(c[:400] for c in contexts[:3])

    system = (
        "You are an evaluation assistant. "
        "Respond with ONLY a valid JSON object containing numeric scores. "
        "No explanation, no markdown, just raw JSON."
    )

    prompt = f"""Rate this RAG response on three metrics. Each score must be a float between 0.0 and 1.0.

QUESTION: {query}

CONTEXT (retrieved chunks):
{ctx_preview}

ANSWER: {answer}

Score definitions:
- faithfulness: Is every claim in the answer directly supported by the context? (1.0 = fully supported, 0.0 = hallucinated)
- context_precision: Are the retrieved context chunks relevant to the question? (1.0 = highly relevant, 0.0 = off-topic)
- answer_relevance: Does the answer actually address the question asked? (1.0 = directly answers, 0.0 = completely irrelevant)

Respond with exactly this JSON format:
{{"faithfulness": 0.0, "context_precision": 0.0, "answer_relevance": 0.0}}"""

    try:
        print("[eval] Running LLM-based RAG evaluation...")
        raw = await get_llm_response(
            prompt=prompt,
            system_prompt=system,
            json_mode=True,
            max_tokens=80,
        )

        scores = json.loads(raw)

        faithfulness = float(scores.get("faithfulness", 0.0))
        context_precision = float(scores.get("context_precision", 0.0))
        answer_relevance = float(scores.get("answer_relevance", 0.0))

        # Clamp to [0, 1]
        faithfulness = max(0.0, min(1.0, faithfulness))
        context_precision = max(0.0, min(1.0, context_precision))
        answer_relevance = max(0.0, min(1.0, answer_relevance))

        print(
            f"[eval] Scores — faithfulness: {faithfulness:.2f}, "
            f"context_precision: {context_precision:.2f}, "
            f"answer_relevance: {answer_relevance:.2f}"
        )

        return EvalResult(
            faithfulness=faithfulness,
            context_precision=context_precision,
            answer_relevance=answer_relevance,
        )

    except Exception as e:
        print(f"[eval] Evaluation failed: {e}")
        return None


def should_retry(eval_result: Optional[EvalResult], threshold: float = 0.7) -> bool:
    """
    Returns True if faithfulness score is below threshold.
    Kept for backwards compatibility (no longer called by critic node).
    """
    if eval_result is None:
        return False
    return eval_result.faithfulness < threshold
