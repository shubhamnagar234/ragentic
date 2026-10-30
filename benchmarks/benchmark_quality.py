"""
RAgentic LLM Response Quality & Evaluator Benchmark Suite
Reuses:
  - Responder prompt formatting from app/services/agents/nodes/responder.py
  - LLM client & streaming from app/services/llm/client.py
  - Custom evaluation metrics from app/services/eval/ragas_eval.py

Compares:
  - Full Pipeline (Config C: Hybrid + Cross-Encoder Rerank)
  - Baseline Without Reranking (Config B: Hybrid RRF without Cross-Encoder)

Measures:
  - Faithfulness, Context Precision, Answer Relevance (using evaluate_response)
  - End-to-end response generation latency (ms)
  - Time-To-First-Token (TTFT) via stream_llm_response (ms)
"""

import sys
import os
import json
import time
import asyncio
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd

# Add root and backend directories to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings
from app.services.llm.client import get_llm_response, stream_llm_response, get_primary_model
from app.services.eval.ragas_eval import evaluate_response, EvalResult
from app.services.retrieval.confidence import compute_confidence, get_confidence_prompt_instruction, ConfidenceLevel
from benchmarks.benchmark_retrieval import RetrievalBenchmarkRunner


class QualityBenchmarkRunner:
    def __init__(self, dataset_path: str, sample_size: int = 5, use_live_services: bool = False):
        self.dataset_path = Path(dataset_path)
        self.sample_size = sample_size
        self.retrieval_runner = RetrievalBenchmarkRunner(
            dataset_path=dataset_path,
            use_live_services=use_live_services,
            iterations=1,
        )
        self.retrieval_runner.setup_corpus()
        self.queries = self.retrieval_runner.queries[:sample_size]

    def build_responder_prompt(self, query: str, chunks: List[Dict[str, Any]]) -> Tuple[str, str, str]:
        """
        Reconstructs the exact prompt and system prompt from app/services/agents/nodes/responder.py.
        """
        confidence_level, _ = compute_confidence(chunks)
        confidence_instruction = get_confidence_prompt_instruction(confidence_level)
        
        context_parts = []
        for i, chunk in enumerate(chunks):
            context_parts.append(f"[Source {i+1}]: {chunk['text']}")
        context = "\n\n".join(context_parts)
        
        system_prompt = f"""You are RAGENTIC, an intelligent knowledge workspace assistant.
You answer questions based strictly on the provided context from the user's documents.

{confidence_instruction}

Always cite which source you used by referencing [Source N] in your answer.
Be concise, accurate, and helpful."""

        user_prompt = f"""Context:
{context}

Question: {query}

Answer:"""

        return user_prompt, system_prompt, confidence_level.value

    async def measure_streaming_ttft(self, prompt: str, system_prompt: str) -> Tuple[str, float, float]:
        """
        Measures Time-To-First-Token (TTFT) and total generation time using stream_llm_response.
        """
        t0 = time.perf_counter()
        ttft = None
        full_answer = ""
        
        async for token in stream_llm_response(prompt, system_prompt=system_prompt, max_tokens=1000):
            if ttft is None:
                ttft = (time.perf_counter() - t0) * 1000.0
            full_answer += token
            
        total_time = (time.perf_counter() - t0) * 1000.0
        if ttft is None:
            ttft = total_time
            
        return full_answer, ttft, total_time

    async def run_quality_benchmark(self, enable_llm: bool = False) -> Dict[str, Any]:
        print("\n" + "=" * 80)
        print("RUNNING LLM RESPONSE QUALITY & EVALUATION BENCHMARK")
        print(f"Model: {get_primary_model()} | Sample Size: {len(self.queries)} questions")
        print("=" * 80)

        if not enable_llm:
            print("\n[NOTE] Live LLM calls were not enabled (--enable-llm flag not passed).")
            print("To protect API limits and prevent unexpected costs, live generation was bypassed.")
            print("Showing prompt validation and evaluator schema verification instead:\n")
            
            sample_q = self.queries[0]
            chunks_c, _ = self.retrieval_runner.execute_configuration("C", sample_q["query"])
            user_p, sys_p, conf = self.build_responder_prompt(sample_q["query"], chunks_c)
            
            print(f"Sample Query: '{sample_q['query']}'")
            print(f"Assigned Confidence: {conf}")
            print(f"Retrieved Chunks: {len(chunks_c)}")
            print(f"System Prompt Length: {len(sys_p)} chars")
            print(f"User Prompt Length: {len(user_p)} chars")
            print("-" * 80)
            print("Evaluator Metrics Defined in app/services/eval/ragas_eval.py:")
            print("  1. Faithfulness: Supported claims / Total claims in answer [0.0 - 1.0]")
            print("  2. Context Precision: Relevance of retrieved chunks to question [0.0 - 1.0]")
            print("  3. Answer Relevance: Directness of answer to question asked [0.0 - 1.0]")
            print("=" * 80 + "\n")
            return {"status": "dry_run", "sample_size": len(self.queries)}

        records = []
        for idx, q_item in enumerate(self.queries):
            qid = q_item["query_id"]
            query_text = q_item["query"]
            print(f"\n[{idx+1}/{len(self.queries)}] Processing: '{query_text[:60]}...'")

            for mode in ["full_pipeline_rerank", "baseline_no_rerank"]:
                config_id = "C" if mode == "full_pipeline_rerank" else "B"
                chunks, _ = self.retrieval_runner.execute_configuration(config_id, query_text)
                contexts = [c["text"] for c in chunks]
                user_p, sys_p, conf = self.build_responder_prompt(query_text, chunks)

                # 1. Measure Generation Latency & TTFT
                try:
                    answer, ttft_ms, gen_ms = await self.measure_streaming_ttft(user_p, sys_p)
                except Exception as e:
                    print(f"  [Generation Error] {mode}: {e}")
                    answer, ttft_ms, gen_ms = f"Error: {e}", 0.0, 0.0

                # 2. Evaluate Answer Quality using evaluate_response
                eval_res = None
                try:
                    if not answer.startswith("Error"):
                        eval_res = await evaluate_response(query_text, answer, contexts)
                except Exception as e:
                    print(f"  [Evaluation Error] {mode}: {e}")

                faith = eval_res.faithfulness if eval_res else None
                c_prec = eval_res.context_precision if eval_res else None
                a_rel = eval_res.answer_relevance if eval_res else None

                print(f"  [{mode}] TTFT: {ttft_ms:.1f}ms | Gen: {gen_ms:.1f}ms | Faith: {faith} | Prec: {c_prec} | Rel: {a_rel}")

                records.append({
                    "query_id": qid,
                    "query": query_text,
                    "mode": mode,
                    "config_id": config_id,
                    "num_contexts": len(contexts),
                    "confidence": conf,
                    "ttft_ms": ttft_ms,
                    "generation_ms": gen_ms,
                    "faithfulness": faith,
                    "context_precision": c_prec,
                    "answer_relevance": a_rel,
                    "answer_preview": answer[:120] + "...",
                })

        df = pd.DataFrame(records)
        results_dir = Path(__file__).resolve().parent / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        
        csv_path = results_dir / "quality_benchmark_raw.csv"
        json_path = results_dir / "quality_benchmark_raw.json"
        df.to_csv(csv_path, index=False)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)

        print("\n" + "=" * 80)
        print("QUALITY & GENERATION LATENCY COMPARISON")
        print("=" * 80)
        grouped = df.groupby("mode").agg({
            "faithfulness": "mean",
            "context_precision": "mean",
            "answer_relevance": "mean",
            "ttft_ms": ["median", lambda x: x.quantile(0.95)],
            "generation_ms": ["median", lambda x: x.quantile(0.95)],
        })
        print(grouped)
        print("=" * 80 + "\n")
        return {"status": "completed", "sample_size": len(self.queries)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run RAgentic Quality & TTFT Benchmark")
    parser.add_argument(
        "--dataset",
        type=str,
        default=str(Path(__file__).resolve().parent / "data" / "benchmark_dataset.json"),
        help="Path to dataset JSON",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=5,
        help="Number of query samples to evaluate (default: 5)",
    )
    parser.add_argument(
        "--enable-llm",
        action="store_true",
        help="Enable live LLM calls via LiteLLM/Gemini (consumes API quota)",
    )
    args = parser.parse_args()

    runner = QualityBenchmarkRunner(dataset_path=args.dataset, sample_size=args.samples)
    asyncio.run(runner.run_quality_benchmark(enable_llm=args.enable_llm))
