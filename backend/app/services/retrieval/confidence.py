import math
from typing import List, Literal, Optional, Tuple, Union
from enum import Enum


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# Configurable confidence thresholds based on 0-1 sigmoid-normalized reranker scores
CONFIDENCE_HIGH_THRESHOLD: float = 0.75
CONFIDENCE_MEDIUM_THRESHOLD: float = 0.50


def compute_confidence(
    reranked_chunks: List[dict],
    context_relevance: Optional[float] = None,
    high_threshold: float = CONFIDENCE_HIGH_THRESHOLD,
    medium_threshold: float = CONFIDENCE_MEDIUM_THRESHOLD,
) -> Tuple[ConfidenceLevel, float]:
    """
    Computes a confidence score before generation.
    Based on:
    - Average reranker score of top-3 chunks (already sigmoid-normalized to [0, 1])
    - Optional RAGAS/evaluator context relevance score in [0, 1]

    Returns (ConfidenceLevel, raw_score)
    """
    # Validate thresholds
    try:
        ht = float(high_threshold)
        mt = float(medium_threshold)
    except (ValueError, TypeError):
        raise ValueError("Confidence thresholds must be numeric floats in [0, 1]")

    if not (math.isfinite(ht) and 0.0 <= ht <= 1.0):
        raise ValueError(f"high_threshold must be a finite float in [0, 1], got {high_threshold}")
    if not (math.isfinite(mt) and 0.0 <= mt <= 1.0):
        raise ValueError(f"medium_threshold must be a finite float in [0, 1], got {medium_threshold}")
    if mt > ht:
        raise ValueError(f"medium_threshold ({mt}) cannot exceed high_threshold ({ht})")

    if not reranked_chunks:
        return ConfidenceLevel.LOW, 0.0

    # Average reranker score of top 3 chunks
    top_chunks = reranked_chunks[:3]
    valid_scores = []
    for c in top_chunks:
        score_val = c.get("reranker_score", 0.0)
        try:
            val = float(score_val)
            if math.isfinite(val):
                # Validate and clamp to [0.0, 1.0]
                valid_scores.append(max(0.0, min(1.0, val)))
            else:
                valid_scores.append(0.0)
        except (ValueError, TypeError):
            valid_scores.append(0.0)

    avg_reranker_score = sum(valid_scores) / len(valid_scores) if valid_scores else 0.0
    normalized_reranker = max(0.0, min(1.0, avg_reranker_score))

    # Combine with context relevance if available (60% reranker, 40% context relevance)
    if context_relevance is not None:
        try:
            cr_val = float(context_relevance)
            if math.isfinite(cr_val):
                clamped_cr = max(0.0, min(1.0, cr_val))
                raw_score = 0.6 * normalized_reranker + 0.4 * clamped_cr
            else:
                # Non-finite context relevance falls back to pure reranker score
                raw_score = normalized_reranker
        except (ValueError, TypeError):
            raw_score = normalized_reranker
    else:
        raw_score = normalized_reranker

    raw_score = max(0.0, min(1.0, raw_score))

    # Map to confidence level using calibrated thresholds
    if raw_score >= ht:
        level = ConfidenceLevel.HIGH
    elif raw_score >= mt:
        level = ConfidenceLevel.MEDIUM
    else:
        level = ConfidenceLevel.LOW

    print(f"[confidence] Score: {raw_score:.3f} -> {level}")
    return level, raw_score


def get_confidence_prompt_instruction(level: Union[ConfidenceLevel, str]) -> str:
    """
    Returns a system prompt instruction based on confidence level.
    Tells the LLM how to frame its response based on context quality.
    """
    if isinstance(level, str):
        try:
            level = ConfidenceLevel(level)
        except ValueError:
            level = ConfidenceLevel.MEDIUM

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
