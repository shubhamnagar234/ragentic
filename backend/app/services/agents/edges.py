from app.services.agents.state import RagenticState
from app.services.eval.ragas_eval import should_retry
from app.services.eval.ragas_eval import EvalResult


def should_retry_edge(state: RagenticState) -> str:
    """
    Conditional edge after critic node.
    Returns "rewrite" if faithfulness is low and retries remain.
    Returns "respond" if quality is acceptable or max retries reached.
    """
    faithfulness = state.get("faithfulness_score")
    retry_count = state.get("retry_count", 0)
    max_retries = 2

    # No eval score available — proceed to respond
    if faithfulness is None:
        print(f"[edges] No faithfulness score — proceeding to respond")
        return "respond"

    # Max retries reached — proceed to respond
    if retry_count >= max_retries:
        print(f"[edges] Max retries ({max_retries}) reached — proceeding to respond")
        return "respond"

    # Low faithfulness — trigger retry
    if faithfulness < 0.7:
        print(f"[edges] Faithfulness {faithfulness:.2f} < 0.7 — triggering retry")
        return "rewrite"

    # Quality acceptable — proceed to respond
    print(f"[edges] Faithfulness {faithfulness:.2f} acceptable — proceeding to respond")
    return "respond"
