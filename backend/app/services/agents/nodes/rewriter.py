from app.services.agents.state import RagenticState
from app.services.llm.client import get_llm_response
from datetime import datetime
import json


async def rewriter_node(state: RagenticState) -> RagenticState:
    """
    Rewrites the query when critic triggers a retry.
    Uses HyDE + multi-query expansion for better retrieval.
    Updates state with improved query and increments retry_count.
    """
    original_query = state["query"]
    retry_count = state.get("retry_count", 0)

    print(
        f"[rewriter] Rewriting query (attempt {retry_count + 1}): {original_query[:50]}..."
    )

    # HyDE — generate a hypothetical answer to use as query
    hyde_prompt = f"""Generate a short hypothetical answer (2-3 sentences) 
that would perfectly answer this question. 
This will be used to improve search results.

Question: {original_query}

Hypothetical answer:"""

    # Multi-query expansion — generate 3 alternative queries
    expansion_prompt = f"""Generate 3 alternative versions of this search query.
Each version should approach the topic from a slightly different angle.
Respond with ONLY a JSON array of 3 strings.

Original query: {original_query}

Example format: ["query 1", "query 2", "query 3"]"""

    try:
        # Get HyDE answer
        hyde_answer = await get_llm_response(hyde_prompt, max_tokens=150)

        # Get expanded queries
        expanded_raw = await get_llm_response(expansion_prompt, max_tokens=200)
        expanded_queries = json.loads(expanded_raw)

        # Combine original + HyDE + best expansion
        rewritten_query = f"{original_query} {hyde_answer} {expanded_queries[0]}"

        print(f"[rewriter] Rewritten query: {rewritten_query[:100]}...")

        event = {
            "agent": "rewriter",
            "status": "completed",
            "message": f"Query rewritten using HyDE + multi-query expansion",
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": {
                "original_query": original_query,
                "expanded_queries": expanded_queries,
            },
        }

        return {
            **state,
            "query": rewritten_query,
            "retry_count": retry_count + 1,
            "timeline_events": state.get("timeline_events", []) + [event],
        }

    except Exception as e:
        print(f"[rewriter] Rewrite failed: {e}. Using original query.")

        event = {
            "agent": "rewriter",
            "status": "failed",
            "message": f"Rewrite failed, using original query",
            "timestamp": datetime.utcnow().isoformat(),
        }

        return {
            **state,
            "retry_count": retry_count + 1,
            "timeline_events": state.get("timeline_events", []) + [event],
        }
