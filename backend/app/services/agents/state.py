from typing import TypedDict, List, Optional, Annotated
from langgraph.graph.message import add_messages


class RagenticState(TypedDict):
    # Query
    query: str
    workspace_id: str
    user_id: str
    source_ids: Optional[List[str]]

    # Routing
    query_type: str
    vector_weight: float
    bm25_weight: float
    top_k: int

    # Retrieval
    dense_chunks: List[dict]
    sparse_chunks: List[dict]
    fused_chunks: List[dict]
    reranked_chunks: List[dict]

    # Evaluation
    faithfulness_score: Optional[float]
    context_precision: Optional[float]
    answer_relevance: Optional[float]
    confidence_level: str
    retry_count: int

    # Memory
    conversation_summary: str
    recent_turns: List[dict]

    # Response
    final_answer: str
    sources_used: List[dict]
    responder_prompt: Optional[str]
    responder_system_prompt: Optional[str]

    # Timeline events for UI
    timeline_events: List[dict]

    # Report / action items
    action_items: List[dict]
    report: Optional[dict]
