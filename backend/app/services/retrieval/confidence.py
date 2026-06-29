from typing import List, Literal
from enum import Enum


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


def compute_confidence(
    reranked_chunks: List[dict],
    context_relevance: float = None,
) -> tuple[ConfidenceLevel, float]:
    """
    Computes a confidence score before generation.
    Based on:
    - Average reranker score of top-3 chunks
    - Optional RAGAS context relevance score

    Returns (ConfidenceLevel, raw_score)
    """
    if not reranked_chunks:
        return ConfidenceLevel.LOW, 0.0

    # Average reranker score of top 3 chunks
    top_chunks = reranked_chunks[:3]
    avg_reranker_score = sum(c.get("reranker_score", 0.0) for c in top_chunks) / len(
        top_chunks
    )

    # Normalize reranker score to 0-1 range
    # Cross-encoder scores typically range from -10 to 10
    normalized_reranker = max(0.0, min(1.0, (avg_reranker_score + 10) / 20))

    # Combine with context relevance if available
    if context_relevance is not None:
        raw_score = 0.6 * normalized_reranker + 0.4 * context_relevance
    else:
        raw_score = normalized_reranker

    # Map to confidence level
    if raw_score >= 0.75:
        level = ConfidenceLevel.HIGH
    elif raw_score >= 0.5:
        level = ConfidenceLevel.MEDIUM
    else:
        level = ConfidenceLevel.LOW

    print(f"[confidence] Score: {raw_score:.3f} → {level}")
    return level, raw_score


def get_confidence_prompt_instruction(level: ConfidenceLevel) -> str:
    """
    Returns a system prompt instruction based on confidence level.
    Tells the LLM how to frame its response based on context quality.
    """
    instructions = {
        ConfidenceLevel.HIGH: (
            "You have high confidence in the retrieved context. "
            "Answer directly and clearly based on the provided sources."
        ),
        ConfidenceLevel.MEDIUM: (
            "You have moderate confidence in the retrieved context. "
            "Answer based on the sources but note any uncertainty."
        ),
        ConfidenceLevel.LOW: (
            "You have low confidence in the retrieved context. "
            "Explicitly tell the user that limited relevant context was found "
            "and suggest they rephrase the question or add more sources."
        ),
    }
    return instructions.get(level, instructions[ConfidenceLevel.MEDIUM])
