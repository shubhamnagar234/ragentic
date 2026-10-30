"""
Integration tests for LangGraph critic routing, retry loop constraints,
and retrieval confidence integration.
"""

import unittest
import asyncio
from unittest.mock import patch, AsyncMock

from app.services.agents.state import RagenticState
from app.services.agents.edges import should_retry_edge
from app.services.agents.nodes.critic import critic_node
from app.services.retrieval.confidence import ConfidenceLevel
from app.services.retrieval.fusion import reciprocal_rank_fusion


class TestLangGraphRoutingAndConfidence(unittest.TestCase):
    def test_critic_node_sets_low_confidence_and_edge_triggers_rewrite(self):
        """When reranked chunks have low relevance, critic sets LOW confidence and edge routes to rewrite."""
        state: RagenticState = {
            "query": "What is quantum computing?",
            "workspace_id": "ws-test",
            "user_id": "usr-1",
            "source_ids": None,
            "query_type": "conceptual",
            "vector_weight": 0.8,
            "bm25_weight": 0.2,
            "top_k": 20,
            "dense_chunks": [],
            "sparse_chunks": [],
            "fused_chunks": [],
            "reranked_chunks": [
                {"chunk_id": "c1", "text": "off-topic chunk", "reranker_score": 0.35},
                {"chunk_id": "c2", "text": "borderline chunk", "reranker_score": 0.40},
            ],
            "faithfulness_score": None,
            "context_precision": None,
            "answer_relevance": None,
            "confidence_level": "MEDIUM",
            "retry_count": 0,
            "conversation_summary": "",
            "recent_turns": [],
            "final_answer": "",
            "sources_used": [],
            "timeline_events": [],
        }

        updated_state = asyncio.run(critic_node(state))

        # 1. Critic sets confidence_level to LOW
        self.assertEqual(updated_state["confidence_level"], ConfidenceLevel.LOW)
        self.assertTrue(updated_state["confidence_level"] == "LOW")

        # 2. Edge routes to rewriter on first attempt (retry_count = 0 < 2)
        next_step = should_retry_edge(updated_state)
        self.assertEqual(next_step, "rewrite")

    def test_critic_node_sets_medium_high_confidence_and_edge_responds(self):
        """When reranked chunks have good relevance, critic sets MEDIUM/HIGH and edge routes to respond."""
        # Medium confidence (0.60)
        state_med: RagenticState = {
            "query": "How does postgres indexing work?",
            "workspace_id": "ws-test",
            "reranked_chunks": [
                {"chunk_id": "c1", "text": "postgres b-tree index", "reranker_score": 0.65},
                {"chunk_id": "c2", "text": "index scan performance", "reranker_score": 0.55},
            ],
            "retry_count": 0,
        }
        res_med = asyncio.run(critic_node(state_med))
        self.assertEqual(res_med["confidence_level"], ConfidenceLevel.MEDIUM)
        self.assertEqual(should_retry_edge(res_med), "respond")

        # High confidence (0.85)
        state_high: RagenticState = {
            "query": "How does postgres indexing work?",
            "workspace_id": "ws-test",
            "reranked_chunks": [
                {"chunk_id": "c1", "text": "exact answer passage", "reranker_score": 0.90},
                {"chunk_id": "c2", "text": "detailed postgres documentation", "reranker_score": 0.80},
            ],
            "retry_count": 0,
        }
        res_high = asyncio.run(critic_node(state_high))
        self.assertEqual(res_high["confidence_level"], ConfidenceLevel.HIGH)
        self.assertEqual(should_retry_edge(res_high), "respond")

    def test_retry_limit_enforced_even_with_low_confidence(self):
        """When retry_count reaches max_retries (2), edge must route to respond even if confidence is LOW."""
        state_max_retry: RagenticState = {
            "query": "obscure query",
            "workspace_id": "ws-test",
            "confidence_level": "LOW",
            "retry_count": 2,  # max_retries reached
        }
        next_step = should_retry_edge(state_max_retry)
        self.assertEqual(next_step, "respond")

        # retry_count = 1 should still allow rewrite
        state_retry_1 = {**state_max_retry, "retry_count": 1}
        self.assertEqual(should_retry_edge(state_retry_1), "rewrite")

    def test_empty_retrieval_triggers_rewrite_then_respond(self):
        """Empty reranked chunks lead to LOW confidence, allowing retry until retry limit."""
        empty_state: RagenticState = {
            "query": "unmatched search term",
            "workspace_id": "ws-test",
            "reranked_chunks": [],
            "retry_count": 0,
        }
        updated_state = asyncio.run(critic_node(empty_state))
        self.assertEqual(updated_state["confidence_level"], ConfidenceLevel.LOW)
        self.assertEqual(should_retry_edge(updated_state), "rewrite")

        # Once retry_count reaches 2
        updated_state["retry_count"] = 2
        self.assertEqual(should_retry_edge(updated_state), "respond")

    def test_rrf_fusion_merges_and_preserves_source_ids(self):
        """RRF fusion properly preserves source_id metadata across dense and sparse inputs."""
        dense = [
            {"chunk_id": "c1", "score": 0.85, "text": "dense text", "source_id": "src-A"},
            {"chunk_id": "c2", "score": 0.70, "text": "dense text 2", "source_id": "src-B"},
        ]
        sparse = [
            {"chunk_id": "c2", "score": 4.5, "text": "sparse text 2", "source_id": "src-B"},
            {"chunk_id": "c3", "score": 2.1, "text": "sparse text 3", "source_id": "src-C"},
        ]
        fused = reciprocal_rank_fusion(dense, sparse, k=60, dense_weight=0.6, sparse_weight=0.4)
        self.assertEqual(len(fused), 3)

        source_map = {c["chunk_id"]: c.get("source_id") for c in fused}
        self.assertEqual(source_map["c1"], "src-A")
        self.assertEqual(source_map["c2"], "src-B")
        self.assertEqual(source_map["c3"], "src-C")


if __name__ == "__main__":
    unittest.main()
