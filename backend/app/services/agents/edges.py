from app.services.agents.state import RagenticState


def should_retry_edge(state: RagenticState) -> str:
    """
    Conditional edge after critic node.

    The critic sets confidence_level based on reranker scores (pre-generation).
    Returns "rewrite" if confidence is LOW and retries remain.
    Returns "respond" if confidence is acceptable or max retries reached.
    """
    confidence_level = state.get("confidence_level", "MEDIUM")
    retry_count = state.get("retry_count", 0)
    max_retries = 2

    # Max retries reached
    if retry_count >= max_retries:
        print(f"[edges] Max retries ({max_retries}) reached -- proceeding to respond")
        return "respond"

    # Low confidence
    if confidence_level == "LOW":
        print(f"[edges] Confidence LOW (retry {retry_count + 1}/{max_retries}) -- triggering rewrite")
        return "rewrite"

    # Confidence acceptable
    print(f"[edges] Confidence {confidence_level} -- proceeding to respond")
    return "respond"
