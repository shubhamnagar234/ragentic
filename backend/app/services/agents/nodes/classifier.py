from app.services.agents.state import RagenticState
from app.services.retrieval.router import route_query
from datetime import datetime


async def classifier_node(state: RagenticState) -> RagenticState:
    """
    Classifies the query and determines retrieval strategy.
    Updates state with query_type, vector_weight, bm25_weight, top_k.
    """
    print(f"[classifier] Classifying query: {state['query'][:50]}...")

    route = await route_query(state["query"])

    # Log timeline event
    event = {
        "agent": "classifier",
        "status": "completed",
        "message": f"Query classified as '{route.query_type}'",
        "timestamp": datetime.utcnow().isoformat(),
    }

    return {
        **state,
        "query_type": route.query_type,
        "vector_weight": route.vector_weight,
        "bm25_weight": route.bm25_weight,
        "top_k": route.top_k,
        "timeline_events": state.get("timeline_events", []) + [event],
    }
