import math
import unittest
from app.services.retrieval.confidence import (
    compute_confidence,
    get_confidence_prompt_instruction,
    ConfidenceLevel,
    CONFIDENCE_HIGH_THRESHOLD,
    CONFIDENCE_MEDIUM_THRESHOLD,
)


class TestConfidenceScoring(unittest.TestCase):
    def test_empty_retrieval_returns_low_and_zero(self):
        """Empty retrieval must return ConfidenceLevel.LOW and 0.0 score."""
        level, score = compute_confidence([])
        self.assertEqual(level, ConfidenceLevel.LOW)
        self.assertEqual(score, 0.0)

    def test_low_scoring_retrieval_classified_as_low(self):
        """Retrieval with low scores (< 0.50) must be classified as LOW."""
        chunks = [
            {"chunk_id": "c1", "reranker_score": 0.35},
            {"chunk_id": "c2", "reranker_score": 0.40},
            {"chunk_id": "c3", "reranker_score": 0.30},
        ]
        level, score = compute_confidence(chunks)
        self.assertEqual(level, ConfidenceLevel.LOW)
        self.assertAlmostEqual(score, 0.35, places=3)
        self.assertLess(score, CONFIDENCE_MEDIUM_THRESHOLD)

    def test_medium_scoring_retrieval_classified_as_medium(self):
        """Retrieval with medium scores (0.50 <= score < 0.75) must be classified as MEDIUM."""
        chunks = [
            {"chunk_id": "c1", "reranker_score": 0.65},
            {"chunk_id": "c2", "reranker_score": 0.60},
            {"chunk_id": "c3", "reranker_score": 0.55},
        ]
        level, score = compute_confidence(chunks)
        self.assertEqual(level, ConfidenceLevel.MEDIUM)
        self.assertAlmostEqual(score, 0.60, places=3)
        self.assertGreaterEqual(score, CONFIDENCE_MEDIUM_THRESHOLD)
        self.assertLess(score, CONFIDENCE_HIGH_THRESHOLD)

    def test_high_scoring_retrieval_classified_as_high(self):
        """Retrieval with strong scores (>= 0.75) must be classified as HIGH."""
        chunks = [
            {"chunk_id": "c1", "reranker_score": 0.92},
            {"chunk_id": "c2", "reranker_score": 0.88},
            {"chunk_id": "c3", "reranker_score": 0.80},
        ]
        level, score = compute_confidence(chunks)
        self.assertEqual(level, ConfidenceLevel.HIGH)
        self.assertAlmostEqual(score, 0.8667, places=3)
        self.assertGreaterEqual(score, CONFIDENCE_HIGH_THRESHOLD)

    def test_only_top_three_chunks_contribute_to_average(self):
        """Only the first 3 chunks should be averaged; 4th and later must not dilute score."""
        chunks = [
            {"chunk_id": "c1", "reranker_score": 0.90},
            {"chunk_id": "c2", "reranker_score": 0.90},
            {"chunk_id": "c3", "reranker_score": 0.90},
            {"chunk_id": "c4", "reranker_score": 0.10},  # should be ignored
            {"chunk_id": "c5", "reranker_score": 0.10},  # should be ignored
        ]
        level, score = compute_confidence(chunks)
        self.assertEqual(level, ConfidenceLevel.HIGH)
        self.assertAlmostEqual(score, 0.90, places=3)

    def test_fewer_than_three_chunks_average_correctly(self):
        """When fewer than 3 chunks are present, averages available chunks."""
        chunks = [
            {"chunk_id": "c1", "reranker_score": 0.80},
            {"chunk_id": "c2", "reranker_score": 0.60},
        ]
        level, score = compute_confidence(chunks)
        self.assertAlmostEqual(score, 0.70, places=3)
        self.assertEqual(level, ConfidenceLevel.MEDIUM)

    def test_optional_context_relevance_combination(self):
        """Context relevance should combine with reranker score via 60/40 weighting."""
        # Top-3 reranker avg = 0.50; context_relevance = 1.0
        # Expected = 0.6 * 0.50 + 0.4 * 1.0 = 0.30 + 0.40 = 0.70
        chunks = [{"chunk_id": "c1", "reranker_score": 0.50}]
        level, score = compute_confidence(chunks, context_relevance=1.0)
        self.assertAlmostEqual(score, 0.70, places=3)
        self.assertEqual(level, ConfidenceLevel.MEDIUM)

        # Context relevance raising score across HIGH threshold
        # Reranker avg = 0.70, context_relevance = 0.90
        # Expected = 0.6 * 0.70 + 0.4 * 0.90 = 0.42 + 0.36 = 0.78 -> HIGH
        level_high, score_high = compute_confidence(reranked_chunks=[{"reranker_score": 0.70}], context_relevance=0.90)
        self.assertAlmostEqual(score_high, 0.78, places=3)
        self.assertEqual(level_high, ConfidenceLevel.HIGH)

    def test_invalid_and_out_of_range_scores_handled_safely(self):
        """Scores out of [0, 1] range or non-numeric types must be clamped or default to 0."""
        chunks = [
            {"chunk_id": "c1", "reranker_score": 1.5},    # clamped to 1.0
            {"chunk_id": "c2", "reranker_score": -0.5},   # clamped to 0.0
            {"chunk_id": "c3", "reranker_score": "bad"},  # invalid, defaults to 0.0
        ]
        # avg = (1.0 + 0.0 + 0.0) / 3 = 0.3333 -> LOW
        level, score = compute_confidence(chunks)
        self.assertEqual(level, ConfidenceLevel.LOW)
        self.assertAlmostEqual(score, 0.3333, places=3)

    def test_out_of_range_context_relevance_clamped(self):
        """Context relevance > 1.0 or < 0.0 must be safely clamped."""
        chunks = [{"chunk_id": "c1", "reranker_score": 0.50}]
        _, score_capped = compute_confidence(chunks, context_relevance=2.5)  # clamped to 1.0
        self.assertAlmostEqual(score_capped, 0.70, places=3)

        _, score_floored = compute_confidence(chunks, context_relevance=-1.0)  # clamped to 0.0
        self.assertAlmostEqual(score_floored, 0.30, places=3)

    def test_confidence_level_string_compatibility(self):
        """ConfidenceLevel enum must compare equal to string constants for LangGraph routing."""
        self.assertEqual(ConfidenceLevel.LOW, "LOW")
        self.assertEqual(ConfidenceLevel.MEDIUM, "MEDIUM")
        self.assertEqual(ConfidenceLevel.HIGH, "HIGH")
        self.assertTrue(ConfidenceLevel.LOW == "LOW")

    def test_prompt_instruction_handles_enum_and_str(self):
        """Prompt instruction helper must accept ConfidenceLevel or raw string."""
        inst_enum = get_confidence_prompt_instruction(ConfidenceLevel.HIGH)
        inst_str = get_confidence_prompt_instruction("HIGH")
        self.assertIn("high confidence", inst_enum.lower())
        self.assertEqual(inst_enum, inst_str)

        # Invalid string defaults to MEDIUM
        inst_fallback = get_confidence_prompt_instruction("UNKNOWN")
        self.assertIn("moderate confidence", inst_fallback.lower())

    def test_nan_and_infinity_in_reranker_scores(self):
        """Non-finite reranker scores (NaN, +inf, -inf) must be treated as 0.0 safely."""
        chunks = [
            {"chunk_id": "c1", "reranker_score": float("nan")},
            {"chunk_id": "c2", "reranker_score": float("inf")},
            {"chunk_id": "c3", "reranker_score": float("-inf")},
        ]
        level, score = compute_confidence(chunks)
        self.assertEqual(level, ConfidenceLevel.LOW)
        self.assertEqual(score, 0.0)

        # Mixed valid and non-finite scores: valid score must be averaged with 0.0
        mixed_chunks = [
            {"chunk_id": "c1", "reranker_score": 0.90},
            {"chunk_id": "c2", "reranker_score": float("nan")},  # becomes 0.0
            {"chunk_id": "c3", "reranker_score": float("inf")},  # becomes 0.0
        ]
        # avg = (0.90 + 0.0 + 0.0) / 3 = 0.30 -> LOW
        m_level, m_score = compute_confidence(mixed_chunks)
        self.assertEqual(m_level, ConfidenceLevel.LOW)
        self.assertAlmostEqual(m_score, 0.30, places=3)

    def test_nan_and_infinity_in_context_relevance(self):
        """Non-finite context_relevance (NaN, +inf, -inf) must fall back to the valid reranker score."""
        chunks = [{"chunk_id": "c1", "reranker_score": 0.80}]

        for bad_cr in [float("nan"), float("inf"), float("-inf")]:
            level, score = compute_confidence(chunks, context_relevance=bad_cr)
            self.assertEqual(level, ConfidenceLevel.HIGH)
            self.assertAlmostEqual(score, 0.80, places=3)

    def test_invalid_thresholds_raise_value_error(self):
        """Thresholds that are non-finite, out of [0, 1], or where medium > high must raise ValueError."""
        valid_chunks = [{"chunk_id": "c1", "reranker_score": 0.80}]

        # Out-of-bounds high_threshold
        with self.assertRaises(ValueError):
            compute_confidence(valid_chunks, high_threshold=1.5)
        with self.assertRaises(ValueError):
            compute_confidence(valid_chunks, high_threshold=-0.1)

        # Out-of-bounds medium_threshold
        with self.assertRaises(ValueError):
            compute_confidence(valid_chunks, medium_threshold=-0.5)
        with self.assertRaises(ValueError):
            compute_confidence(valid_chunks, medium_threshold=1.1)

        # medium_threshold > high_threshold
        with self.assertRaises(ValueError):
            compute_confidence(valid_chunks, high_threshold=0.50, medium_threshold=0.75)

        # Non-finite thresholds
        with self.assertRaises(ValueError):
            compute_confidence(valid_chunks, high_threshold=float("nan"))
        with self.assertRaises(ValueError):
            compute_confidence(valid_chunks, high_threshold=float("inf"))
        with self.assertRaises(ValueError):
            compute_confidence(valid_chunks, medium_threshold=float("nan"))
        with self.assertRaises(ValueError):
            compute_confidence(valid_chunks, medium_threshold=float("-inf"))

        # Non-numeric thresholds
        with self.assertRaises(ValueError):
            compute_confidence(valid_chunks, high_threshold="invalid_string")


if __name__ == "__main__":
    unittest.main()
