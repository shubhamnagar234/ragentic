"""
Unit tests for cross-encoder reranking behavior, candidate ordering, thresholding, and parameter validation.
"""

import unittest
from unittest.mock import patch, MagicMock
import math
import numpy as np

from app.services.retrieval.reranker import rerank_chunks


class FakeReranker:
    def __init__(self, scores):
        self.scores = scores

    def predict(self, pairs):
        # Return preconfigured scores matching the number of pairs
        return self.scores[:len(pairs)]


class TestCrossEncoderReranker(unittest.TestCase):
    def test_top_k_behavior_without_threshold(self):
        """When threshold=None (default), returns exactly top_k candidates sorted descending."""
        chunks = [
            {"chunk_id": "c1", "text": "PostgreSQL indexing"},
            {"chunk_id": "c2", "text": "Redis caching"},
            {"chunk_id": "c3", "text": "Qdrant vector search"},
            {"chunk_id": "c4", "text": "BM25 keyword search"},
            {"chunk_id": "c5", "text": "LangGraph agent workflow"},
        ]
        # Raw logits: c3 highest, c1 second, c5 third, c2 fourth, c4 lowest
        mock_logits = [-1.0, -3.0, 4.5, -5.0, 1.2]
        fake = FakeReranker(mock_logits)

        with patch("app.services.retrieval.reranker.get_reranker", return_value=fake):
            results = rerank_chunks(query="vector search", chunks=chunks, top_k=3, threshold=None)

        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]["chunk_id"], "c3")
        self.assertEqual(results[1]["chunk_id"], "c5")
        self.assertEqual(results[2]["chunk_id"], "c1")
        self.assertGreater(results[0]["reranker_score"], results[1]["reranker_score"])
        self.assertGreater(results[1]["reranker_score"], results[2]["reranker_score"])

    def test_correct_descending_score_ordering(self):
        """Returned chunks must be strictly ordered descending by reranker_score."""
        chunks = [{"chunk_id": f"c{i}", "text": f"text {i}"} for i in range(6)]
        mock_logits = [0.5, -2.1, 3.8, 1.1, -0.4, 2.9]
        fake = FakeReranker(mock_logits)

        with patch("app.services.retrieval.reranker.get_reranker", return_value=fake):
            results = rerank_chunks(query="test", chunks=chunks, top_k=5)

        for i in range(len(results) - 1):
            self.assertGreaterEqual(
                results[i]["reranker_score"],
                results[i + 1]["reranker_score"],
                f"Rank {i} score ({results[i]['reranker_score']}) must be >= Rank {i+1} score ({results[i+1]['reranker_score']})"
            )

    def test_sigmoid_preserves_monotonicity_of_raw_logits(self):
        """Sigmoid function is strictly monotonic: ranking by sigmoid must be identical to raw logits."""
        chunks = [{"chunk_id": f"c{i}", "text": f"text {i}"} for i in range(5)]
        raw_logits = [5.2, -8.1, 0.0, -1.5, 2.3]
        fake = FakeReranker(raw_logits)

        with patch("app.services.retrieval.reranker.get_reranker", return_value=fake):
            results = rerank_chunks(query="test", chunks=chunks, top_k=5)

        # Expected descending order by raw logits: c0 (5.2), c4 (2.3), c2 (0.0), c3 (-1.5), c1 (-8.1)
        expected_ids = ["c0", "c4", "c2", "c3", "c1"]
        actual_ids = [c["chunk_id"] for c in results]
        self.assertEqual(actual_ids, expected_ids)

        # Verify exact sigmoid values
        for c, expected_id in zip(results, expected_ids):
            orig_idx = int(expected_id[1:])
            expected_sigmoid = 1.0 / (1.0 + math.exp(-raw_logits[orig_idx]))
            self.assertAlmostEqual(c["reranker_score"], expected_sigmoid, places=5)

    def test_threshold_filtering_with_minimum_candidate_fallback(self):
        """When threshold is set and fewer than min_k pass, fallback returns min_k top candidates."""
        chunks = [{"chunk_id": f"c{i}", "text": f"chunk {i}"} for i in range(5)]
        # Logits: c0 has sigmoid ~0.95 (> 0.7); all others have sigmoid < 0.7
        # c1 has logit 0.0 (sigmoid 0.50), c2 has -1.0 (sigmoid 0.27), c3 has -2.0, c4 has -3.0
        mock_logits = [3.0, 0.0, -1.0, -2.0, -3.0]
        fake = FakeReranker(mock_logits)

        with patch("app.services.retrieval.reranker.get_reranker", return_value=fake):
            # Only 1 candidate (c0) crosses threshold 0.7, but min_k=3 forces top-3 return
            results = rerank_chunks(query="query", chunks=chunks, top_k=5, threshold=0.7, min_k=3)

        self.assertEqual(len(results), 3, "Expected min_k=3 fallback candidates")
        self.assertEqual(results[0]["chunk_id"], "c0")
        self.assertEqual(results[1]["chunk_id"], "c1")
        self.assertEqual(results[2]["chunk_id"], "c2")

    def test_threshold_filtering_when_more_than_min_k_pass(self):
        """When more than min_k candidates exceed threshold, all passing candidates up to top_k are returned."""
        chunks = [{"chunk_id": f"c{i}", "text": f"chunk {i}"} for i in range(5)]
        # Logits: c0, c1, c2, c3 all have sigmoid > 0.4 (logit > -0.405)
        mock_logits = [2.0, 1.5, 0.5, 0.0, -4.0]  # c4 has sigmoid ~0.018 (< 0.4)
        fake = FakeReranker(mock_logits)

        with patch("app.services.retrieval.reranker.get_reranker", return_value=fake):
            results = rerank_chunks(query="query", chunks=chunks, top_k=3, threshold=0.4, min_k=2)

        # 4 chunks passed, but top_k=3 caps the output
        self.assertEqual(len(results), 3)
        self.assertNotIn("c4", [c["chunk_id"] for c in results])

    def test_empty_and_small_candidate_lists(self):
        """Empty inputs return [] and inputs smaller than top_k return all available candidates."""
        # Empty input
        self.assertEqual(rerank_chunks(query="test", chunks=[]), [])

        # Fewer candidates than top_k
        chunks = [
            {"chunk_id": "c1", "text": "PostgreSQL"},
            {"chunk_id": "c2", "text": "Redis"},
        ]
        fake = FakeReranker([1.0, 2.0])
        with patch("app.services.retrieval.reranker.get_reranker", return_value=fake):
            results = rerank_chunks(query="db", chunks=chunks, top_k=5)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["chunk_id"], "c2")
        self.assertEqual(results[1]["chunk_id"], "c1")

    def test_invalid_parameters_raise_value_error(self):
        """Invalid top_k, min_k, or threshold must raise ValueError."""
        valid_chunks = [{"chunk_id": "c1", "text": "sample"}]

        # Invalid top_k
        with self.assertRaises(ValueError):
            rerank_chunks(query="q", chunks=valid_chunks, top_k=0)
        with self.assertRaises(ValueError):
            rerank_chunks(query="q", chunks=valid_chunks, top_k=-2)
        with self.assertRaises(ValueError):
            rerank_chunks(query="q", chunks=valid_chunks, top_k="invalid")
        with self.assertRaises(ValueError):
            rerank_chunks(query="q", chunks=valid_chunks, top_k=True)
        with self.assertRaises(ValueError):
            rerank_chunks(query="q", chunks=valid_chunks, top_k=False)

        # Invalid min_k
        with self.assertRaises(ValueError):
            rerank_chunks(query="q", chunks=valid_chunks, min_k=0)
        with self.assertRaises(ValueError):
            rerank_chunks(query="q", chunks=valid_chunks, min_k=-1)
        with self.assertRaises(ValueError):
            rerank_chunks(query="q", chunks=valid_chunks, min_k=True)
        with self.assertRaises(ValueError):
            rerank_chunks(query="q", chunks=valid_chunks, min_k=False)

        # Invalid threshold
        with self.assertRaises(ValueError):
            rerank_chunks(query="q", chunks=valid_chunks, threshold=1.5)
        with self.assertRaises(ValueError):
            rerank_chunks(query="q", chunks=valid_chunks, threshold=-0.1)
        with self.assertRaises(ValueError):
            rerank_chunks(query="q", chunks=valid_chunks, threshold=float("nan"))
        with self.assertRaises(ValueError):
            rerank_chunks(query="q", chunks=valid_chunks, threshold="non_numeric")
        with self.assertRaises(ValueError):
            rerank_chunks(query="q", chunks=valid_chunks, threshold=True)
        with self.assertRaises(ValueError):
            rerank_chunks(query="q", chunks=valid_chunks, threshold=False)

    def test_preservation_of_original_chunk_metadata(self):
        """All metadata fields on chunks must be preserved alongside reranker_score."""
        chunks = [
            {
                "chunk_id": "c1",
                "text": "Vector search in Qdrant",
                "source_id": "src-vector-guide",
                "parent_id": "parent-100",
                "metadata": {"section": "embedding", "page": 4},
                "doc_id": "doc-01",
            }
        ]
        fake = FakeReranker([2.5])
        with patch("app.services.retrieval.reranker.get_reranker", return_value=fake):
            results = rerank_chunks(query="vector search", chunks=chunks, top_k=1)

        self.assertEqual(len(results), 1)
        r = results[0]
        self.assertEqual(r["chunk_id"], "c1")
        self.assertEqual(r["text"], "Vector search in Qdrant")
        self.assertEqual(r["source_id"], "src-vector-guide")
        self.assertEqual(r["parent_id"], "parent-100")
        self.assertEqual(r["metadata"], {"section": "embedding", "page": 4})
        self.assertEqual(r["doc_id"], "doc-01")
        self.assertIn("reranker_score", r)
        self.assertAlmostEqual(r["reranker_score"], 1.0 / (1.0 + math.exp(-2.5)), places=5)


if __name__ == "__main__":
    unittest.main()
