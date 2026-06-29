from typing import List, Optional
from dataclasses import dataclass


@dataclass
class EvalResult:
    faithfulness: float
    context_precision: float
    answer_relevance: float


async def evaluate_response(
    query: str,
    answer: str,
    contexts: List[str],
) -> Optional[EvalResult]:
    """
    Evaluates a RAG response using RAGAS metrics.
    - faithfulness: is the answer grounded in the context?
    - context_precision: are the retrieved chunks relevant?
    - answer_relevance: does the answer address the query?
    Returns EvalResult or None if evaluation fails.
    """
    try:
        from ragas import evaluate
        from ragas.metrics import faithfulness, context_precision, answer_relevancy
        from datasets import Dataset

        print(f"[ragas_eval] Evaluating response...")

        data = {
            "question": [query],
            "answer": [answer],
            "contexts": [contexts],
        }

        dataset = Dataset.from_dict(data)

        result = evaluate(
            dataset,
            metrics=[faithfulness, context_precision, answer_relevancy],
        )

        scores = result.to_pandas()

        return EvalResult(
            faithfulness=float(scores["faithfulness"].iloc[0]),
            context_precision=float(scores["context_precision"].iloc[0]),
            answer_relevance=float(scores["answer_relevancy"].iloc[0]),
        )

    except Exception as e:
        print(f"[ragas_eval] Evaluation failed: {e}")
        return None


def should_retry(eval_result: Optional[EvalResult], threshold: float = 0.7) -> bool:
    """
    Returns True if faithfulness score is below threshold.
    Triggers the critic-retry loop in the agent graph.
    """
    if eval_result is None:
        return False
    return eval_result.faithfulness < threshold
