"""
Unified Entry Point for RAgentic Benchmark Suite
Executes retrieval benchmarks, latency trials, and quality tests,
then generates markdown and raw data artifacts.
"""

import sys
import argparse
import asyncio
from pathlib import Path

# Add root and backend directories to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from benchmarks.benchmark_retrieval import RetrievalBenchmarkRunner
from benchmarks.benchmark_quality import QualityBenchmarkRunner


def main():
    parser = argparse.ArgumentParser(description="RAgentic Comprehensive Benchmark Suite")
    parser.add_argument(
        "--dataset",
        type=str,
        default=str(Path(__file__).resolve().parent / "data" / "benchmark_dataset.json"),
        help="Path to evaluation dataset JSON",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=3,
        help="Number of repeated runs per query for latency statistics (default: 3)",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Attempt connecting to live external services (Qdrant/Redis) instead of in-memory",
    )
    parser.add_argument(
        "--enable-llm",
        action="store_true",
        help="Enable live LLM API calls for generation & evaluator benchmarks",
    )
    parser.add_argument(
        "--llm-samples",
        type=int,
        default=5,
        help="Number of query samples to evaluate with LLM (default: 5)",
    )
    args = parser.parse_args()

    print("\n" + "#" * 80)
    print(" RAGENTIC REPRODUCIBLE BENCHMARK SUITE")
    print("#" * 80)

    # 1. Run Retrieval & Latency Benchmarks
    print("\n[STEP 1/2] Executing Retrieval Quality & Latency Benchmark...")
    retrieval_runner = RetrievalBenchmarkRunner(
        dataset_path=args.dataset,
        use_live_services=args.live,
        iterations=args.iterations,
    )
    retrieval_summary = retrieval_runner.run_benchmark()

    # 2. Run LLM Quality & TTFT Benchmark
    print("\n[STEP 2/2] Executing LLM Quality & Evaluator Benchmark...")
    quality_runner = QualityBenchmarkRunner(
        dataset_path=args.dataset,
        sample_size=args.llm_samples,
        use_live_services=args.live,
    )
    asyncio.run(quality_runner.run_quality_benchmark(enable_llm=args.enable_llm))

    print("\n" + "#" * 80)
    print(" BENCHMARK EXECUTION COMPLETED")
    print(f" Artifacts generated in: {Path(__file__).resolve().parent / 'results'}")
    print("#" * 80 + "\n")


if __name__ == "__main__":
    main()
