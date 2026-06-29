from typing import Literal
from pydantic import BaseModel
from app.services.llm.client import get_llm_response


class QueryRoute(BaseModel):
    query_type: Literal["factual", "conceptual", "comparative", "procedural", "code"]
    vector_weight: float
    bm25_weight: float
    top_k: int
    reasoning: str


# Default configs per query type
ROUTE_CONFIGS = {
    "factual": {
        "vector_weight": 0.3,
        "bm25_weight": 0.7,
        "top_k": 20,
    },
    "conceptual": {
        "vector_weight": 0.8,
        "bm25_weight": 0.2,
        "top_k": 20,
    },
    "comparative": {
        "vector_weight": 0.6,
        "bm25_weight": 0.4,
        "top_k": 25,
    },
    "procedural": {
        "vector_weight": 0.5,
        "bm25_weight": 0.5,
        "top_k": 20,
    },
    "code": {
        "vector_weight": 0.4,
        "bm25_weight": 0.6,
        "top_k": 15,
    },
}


async def route_query(query: str) -> QueryRoute:
    """
    Classifies a query and returns the optimal retrieval configuration.
    Uses Gemini Flash for fast, cheap classification.
    """
    prompt = f"""Classify this query into one of these types:
- factual: specific facts, names, dates, numbers ("what did the CEO say about revenue?")
- conceptual: ideas, explanations, understanding ("how does RAG work?")
- comparative: comparing things ("what are the differences between X and Y?")
- procedural: how-to, steps, process ("how do I set up authentication?")
- code: code-related questions ("how is the auth function implemented?")

Query: "{query}"

Respond with ONLY a JSON object in this exact format:
{{
  "query_type": "factual|conceptual|comparative|procedural|code",
  "reasoning": "one sentence explanation"
}}"""

    try:
        response = await get_llm_response(prompt, json_mode=True)
        import json

        data = json.loads(response)
        query_type = data.get("query_type", "conceptual")
        config = ROUTE_CONFIGS.get(query_type, ROUTE_CONFIGS["conceptual"])

        return QueryRoute(
            query_type=query_type,
            reasoning=data.get("reasoning", ""),
            **config,
        )

    except Exception as e:
        print(f"[router] Classification failed, using default: {e}")
        return QueryRoute(
            query_type="conceptual",
            reasoning="Default fallback",
            **ROUTE_CONFIGS["conceptual"],
        )
