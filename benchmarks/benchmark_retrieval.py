"""
RAgentic Retrieval & Latency Benchmark Suite
Compares:
  Config A: Qdrant-only dense vector retrieval
  Config B: Qdrant + BM25 + Reciprocal Rank Fusion (RRF)
  Config C: Hybrid retrieval (Qdrant + BM25 + RRF) + Cross-Encoder Reranking

Measures:
  - Retrieval Quality: Recall@5, Hit-Rate@5, MRR, Precision@5
  - Latency (ms): Retrieval latency, reranking latency, end-to-end retrieval latency
  - Statistical summary: sample count, mean, median (p50), p95, min, max, failure rate
  - Cold-start vs Warm-run separation
"""

import sys
import os
import json
import time
import math
import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple
import numpy as np
import pandas as pd

# Add backend directory to sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings
from app.services.ingestion.chunker import chunk_text_hierarchical
from app.services.ingestion.embedder import embed_chunks, embed_query, get_text_model
from app.services.retrieval.sparse import build_bm25_index
from app.services.retrieval.fusion import reciprocal_rank_fusion
from app.services.retrieval.reranker import rerank_chunks, get_reranker
import app.services.retrieval.dense as dense_module
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct, Filter, FieldCondition, MatchValue


class RetrievalBenchmarkRunner:
    def __init__(self, dataset_path: str, use_live_services: bool = False, iterations: int = 3):
        self.dataset_path = Path(dataset_path)
        self.use_live_services = use_live_services
        self.iterations = iterations
        self.workspace_id = "ws-benchmark-ragentic"
        self.collection_name = "benchmark-collection"

        # Load dataset
        with open(self.dataset_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

        self.documents = self.data["documents"]
        self.queries = self.data["queries"]

        self.qdrant_client = None
        self.chunks: List[Dict[str, Any]] = []
        self.bm25_index = None
        self.doc_to_chunk_ids: Dict[str, List[str]] = {}
        self.chunk_id_to_doc_id: Dict[str, str] = {}

    def setup_corpus(self):
        """Chunks documents, builds in-memory or live Qdrant collection, and builds BM25 index."""
        print("\n" + "=" * 60)
        print("SETTING UP BENCHMARK CORPUS & INDICES")
        print("=" * 60)

        # 1. Chunk documents hierarchically
        all_child_chunks = []
        for doc in self.documents:
            doc_id = doc["doc_id"]
            chunks = chunk_text_hierarchical(
                text=doc["text"],
                parent_chunk_size=1000,
                child_chunk_size=150,
                overlap=20,
            )
            child_chunks = [c for c in chunks if c.chunk_type == "child"]
            for c in child_chunks:
                c.metadata = {"doc_id": doc_id, "source_id": doc_id, "workspace_id": self.workspace_id}
                if doc_id not in self.doc_to_chunk_ids:
                    self.doc_to_chunk_ids[doc_id] = []
                self.doc_to_chunk_ids[doc_id].append(c.chunk_id)
                self.chunk_id_to_doc_id[c.chunk_id] = doc_id
            all_child_chunks.extend(child_chunks)

        print(f"[Corpus] {len(self.documents)} documents partitioned into {len(all_child_chunks)} child chunks.")

        # 2. Embed chunks using project sentence-transformer
        print(f"[Embedding] Embedding child chunks using model: {settings.EMBEDDING_MODEL_TEXT}...")
        t0 = time.perf_counter()
        embedded_items = embed_chunks(all_child_chunks, is_code=False)
        embed_time = (time.perf_counter() - t0) * 1000
        print(f"[Embedding] Completed in {embed_time:.2f} ms ({len(embedded_items)} vectors, dim={len(embedded_items[0]['vector'])}).")

        self.chunks = [
            {
                "chunk_id": item["chunk_id"],
                "text": item["text"],
                "parent_id": item["parent_id"],
                "source_id": item["metadata"]["source_id"],
                "workspace_id": self.workspace_id,
                "metadata": item["metadata"],
            }
            for item in embedded_items
        ]

        # 3. Setup Qdrant
        if self.use_live_services:
            try:
                print(f"[Qdrant] Connecting to live Qdrant at {settings.QDRANT_URL}...")
                client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY or None, timeout=5)
                client.get_collections()
                self.qdrant_client = client
                self.collection_name = settings.QDRANT_COLLECTION
                print(f"[Qdrant] Connected to live Qdrant. Using collection: {self.collection_name}")
            except Exception as e:
                print(f"[Qdrant] Live connection failed ({e}). Falling back to standalone in-memory Qdrant engine.")
                self.qdrant_client = QdrantClient(":memory:")
                self.collection_name = "benchmark-minilm"
        else:
            print("[Qdrant] Initializing standalone embedded Qdrant instance (:memory:)...")
            self.qdrant_client = QdrantClient(":memory:")
            self.collection_name = "benchmark-minilm"

        # Recreate collection in Qdrant
        dim = len(embedded_items[0]["vector"])
        collections = [c.name for c in self.qdrant_client.get_collections().collections]
        if self.collection_name in collections:
            self.qdrant_client.delete_collection(self.collection_name)

        self.qdrant_client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )

        points = [
            PointStruct(
                id=item["chunk_id"],
                vector=item["vector"],
                payload={
                    "text": item["text"],
                    "parent_id": item["parent_id"],
                    "source_id": item["metadata"]["source_id"],
                    "workspace_id": self.workspace_id,
                },
            )
            for item in embedded_items
        ]
        self.qdrant_client.upsert(collection_name=self.collection_name, points=points)
        print(f"[Qdrant] Indexed {len(points)} points into collection '{self.collection_name}'.")

        # Patch dense module client so production dense_search uses this client & collection
        dense_module._client = self.qdrant_client
        dense_module.settings.QDRANT_COLLECTION = self.collection_name

        # 4. Build BM25 index using production build_bm25_index
        print("[BM25] Building BM25Okapi lexical index...")
        self.bm25_index = build_bm25_index(self.chunks)
        print(f"[BM25] Indexed {len(self.chunks)} chunk texts.")

        # Warm up cross-encoder model
        print(f"[Reranker] Pre-loading reranker model: {settings.RERANKER_MODEL}...")
        get_reranker()
        print("[Setup] Corpus setup complete.\n")

    def run_dense_search(self, query: str, top_k: int = 20) -> List[Dict[str, Any]]:
        """Executes Qdrant dense vector search."""
        query_vector = embed_query(query, is_code=False)
        search_filter = Filter(
            must=[FieldCondition(key="workspace_id", match=MatchValue(value=self.workspace_id))]
        )
        response = self.qdrant_client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=search_filter,
            limit=top_k,
            with_payload=True,
        )
        chunks = []
        for result in response.points:
            chunks.append({
                "chunk_id": str(result.id),
                "score": float(result.score),
                "text": result.payload.get("text", ""),
                "parent_id": result.payload.get("parent_id"),
                "source_id": result.payload.get("source_id"),
                "metadata": result.payload,
            })
        return chunks

    def run_bm25_search(self, query: str, top_k: int = 20) -> List[Dict[str, Any]]:
        """Executes BM25 keyword search using production BM25Okapi index."""
        tokenized_query = query.lower().split()
        scores = self.bm25_index.get_scores(tokenized_query)
        scored = [
            {
                "chunk_id": self.chunks[i]["chunk_id"],
                "score": float(scores[i]),
                "text": self.chunks[i]["text"],
                "source_id": self.chunks[i].get("source_id"),
            }
            for i in range(len(self.chunks))
        ]
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def execute_configuration(
        self, config_name: str, query: str, vector_weight: float = 0.6, bm25_weight: float = 0.4
    ) -> Tuple[List[Dict[str, Any]], Dict[str, float]]:
        """
        Executes one configuration:
          'A': Dense only
          'B': Hybrid (Dense + BM25 + RRF)
          'C': Hybrid + Cross-Encoder Rerank
        Returns (top_5_chunks, latency_dict_ms)
        """
        latencies = {}
        t_total_start = time.perf_counter()

        if config_name == "A":
            # Config A: Dense Vector Only
            t_ret_start = time.perf_counter()
            dense_results = self.run_dense_search(query, top_k=5)
            ret_lat = (time.perf_counter() - t_ret_start) * 1000
            total_lat = (time.perf_counter() - t_total_start) * 1000

            latencies["retrieval_ms"] = ret_lat
            latencies["reranking_ms"] = 0.0
            latencies["total_ms"] = total_lat
            return dense_results, latencies

        elif config_name == "B":
            # Config B: Dense + BM25 + RRF
            t_ret_start = time.perf_counter()
            dense_results = self.run_dense_search(query, top_k=20)
            sparse_results = self.run_bm25_search(query, top_k=20)
            fused = reciprocal_rank_fusion(
                dense_results=dense_results,
                sparse_results=sparse_results,
                k=60,
                dense_weight=vector_weight,
                sparse_weight=bm25_weight,
            )
            ret_lat = (time.perf_counter() - t_ret_start) * 1000
            total_lat = (time.perf_counter() - t_total_start) * 1000

            latencies["retrieval_ms"] = ret_lat
            latencies["reranking_ms"] = 0.0
            latencies["total_ms"] = total_lat
            return fused[:5], latencies

        elif config_name == "C":
            # Config C: Hybrid + Cross-Encoder Reranker
            t_ret_start = time.perf_counter()
            dense_results = self.run_dense_search(query, top_k=20)
            sparse_results = self.run_bm25_search(query, top_k=20)
            fused = reciprocal_rank_fusion(
                dense_results=dense_results,
                sparse_results=sparse_results,
                k=60,
                dense_weight=vector_weight,
                sparse_weight=bm25_weight,
            )
            ret_lat = (time.perf_counter() - t_ret_start) * 1000

            # Cross-encoder rerank
            t_rerank_start = time.perf_counter()
            reranked = rerank_chunks(
                query=query,
                chunks=fused[:20],
                top_k=5,
            )
            rerank_lat = (time.perf_counter() - t_rerank_start) * 1000
            total_lat = (time.perf_counter() - t_total_start) * 1000

            latencies["retrieval_ms"] = ret_lat
            latencies["reranking_ms"] = rerank_lat
            latencies["total_ms"] = total_lat
            return reranked, latencies

        else:
            raise ValueError(f"Unknown configuration: {config_name}")

    def evaluate_query(
        self, retrieved_chunks: List[Dict[str, Any]], relevant_doc_ids: List[str]
    ) -> Dict[str, float]:
        """Calculates Recall@5, Hit-Rate@5, MRR, Precision@5."""
        if not retrieved_chunks:
            return {"recall@5": 0.0, "hit_rate@5": 0.0, "mrr": 0.0, "precision@5": 0.0}

        # Determine all relevant child chunk IDs for the ground truth documents
        target_chunk_ids = set()
        for doc_id in relevant_doc_ids:
            for c_id in self.doc_to_chunk_ids.get(doc_id, []):
                target_chunk_ids.add(c_id)

        retrieved_ids = [c["chunk_id"] for c in retrieved_chunks[:5]]

        # Check relevance
        relevant_matches = [cid for cid in retrieved_ids if cid in target_chunk_ids]
        num_relevant_retrieved = len(relevant_matches)

        # Precision@5
        precision_at_5 = num_relevant_retrieved / 5.0

        # Recall@5: fraction of available ground truth chunks retrieved (capped at 5)
        denom = min(len(target_chunk_ids), 5) if target_chunk_ids else 1
        recall_at_5 = num_relevant_retrieved / float(denom)

        # Hit Rate@5: 1 if at least one relevant chunk is in top 5, else 0
        hit_rate_at_5 = 1.0 if num_relevant_retrieved > 0 else 0.0

        # MRR (Mean Reciprocal Rank): 1 / rank of first relevant chunk
        rr = 0.0
        for rank, cid in enumerate(retrieved_ids, start=1):
            if cid in target_chunk_ids:
                rr = 1.0 / rank
                break

        return {
            "recall@5": recall_at_5,
            "hit_rate@5": hit_rate_at_5,
            "mrr": rr,
            "precision@5": precision_at_5,
        }

    def run_benchmark(self) -> Dict[str, Any]:
        """Runs benchmark across all configurations and iterations."""
        self.setup_corpus()

        configs = [
            ("A", "Qdrant Vector Only"),
            ("B", "Hybrid (Qdrant + BM25 + RRF)"),
            ("C", "Hybrid + Cross-Encoder Rerank"),
        ]

        raw_observations = []

        print("=" * 60)
        print(f"RUNNING BENCHMARK ({len(self.queries)} queries, {self.iterations} iterations per config)")
        print("=" * 60)

        for config_id, config_label in configs:
            print(f"\n---> Evaluating Config {config_id}: {config_label}...")

            for iter_idx in range(self.iterations):
                is_cold = (iter_idx == 0)
                run_type = "cold" if is_cold else "warm"

                for q_idx, q_item in enumerate(self.queries):
                    query_id = q_item["query_id"]
                    query_text = q_item["query"]
                    query_type = q_item.get("query_type", "conceptual")
                    relevant_docs = q_item["relevant_doc_ids"]

                    # Adaptive weights from router definitions
                    if query_type == "factual":
                        v_weight, b_weight = 0.3, 0.7
                    elif query_type == "conceptual":
                        v_weight, b_weight = 0.8, 0.2
                    elif query_type == "comparative":
                        v_weight, b_weight = 0.6, 0.4
                    elif query_type == "code":
                        v_weight, b_weight = 0.4, 0.6
                    else:
                        v_weight, b_weight = 0.5, 0.5

                    try:
                        top_chunks, lats = self.execute_configuration(
                            config_name=config_id,
                            query=query_text,
                            vector_weight=v_weight,
                            bm25_weight=b_weight,
                        )
                        eval_metrics = self.evaluate_query(top_chunks, relevant_docs)
                        is_success = len(top_chunks) > 0
                        error_msg = None
                    except Exception as e:
                        top_chunks = []
                        lats = {"retrieval_ms": 0.0, "reranking_ms": 0.0, "total_ms": 0.0}
                        eval_metrics = {"recall@5": 0.0, "hit_rate@5": 0.0, "mrr": 0.0, "precision@5": 0.0}
                        is_success = False
                        error_msg = str(e)

                    raw_observations.append({
                        "config_id": config_id,
                        "config_name": config_label,
                        "iteration": iter_idx + 1,
                        "run_type": run_type,
                        "query_id": query_id,
                        "query_type": query_type,
                        "query_text": query_text,
                        "relevant_docs": relevant_docs,
                        "retrieved_chunk_ids": [c["chunk_id"] for c in top_chunks],
                        "recall@5": eval_metrics["recall@5"],
                        "hit_rate@5": eval_metrics["hit_rate@5"],
                        "mrr": eval_metrics["mrr"],
                        "precision@5": eval_metrics["precision@5"],
                        "retrieval_latency_ms": lats["retrieval_ms"],
                        "reranking_latency_ms": lats["reranking_ms"],
                        "total_latency_ms": lats["total_ms"],
                        "success": is_success,
                        "error": error_msg,
                    })

        df = pd.DataFrame(raw_observations)

        # Save raw outputs
        results_dir = Path(__file__).resolve().parent / "results"
        results_dir.mkdir(parents=True, exist_ok=True)

        csv_path = results_dir / "retrieval_benchmark_raw.csv"
        json_path = results_dir / "retrieval_benchmark_raw.json"

        df.to_csv(csv_path, index=False)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(raw_observations, f, indent=2)

        print(f"\n[Artifacts] Saved raw observations to:\n  {csv_path}\n  {json_path}")

        # Compute summary metrics
        summary_results = self.compute_summary(df)
        return summary_results

    def compute_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculates aggregated quality and latency statistics."""
        summary = {"retrieval_quality": {}, "latency": {}}

        # 1. Retrieval Quality (aggregated over all trials)
        print("\n" + "=" * 80)
        print("RETRIEVAL QUALITY BENCHMARK RESULTS (A vs B vs C)")
        print("=" * 80)
        print(f"{'Config':<35} | {'Recall@5':<10} | {'Hit-Rate@5':<12} | {'MRR':<8} | {'Precision@5':<12} | {'Evaluated Qs':<12}")
        print("-" * 80)

        for config_id in ["A", "B", "C"]:
            sub_df = df[df["config_id"] == config_id]
            rec = sub_df["recall@5"].mean()
            hr = sub_df["hit_rate@5"].mean()
            mrr = sub_df["mrr"].mean()
            prec = sub_df["precision@5"].mean()
            config_name = sub_df["config_name"].iloc[0]
            evaluated_qs = len(sub_df["query_id"].unique())

            summary["retrieval_quality"][config_id] = {
                "config_name": config_name,
                "recall@5": float(rec),
                "hit_rate@5": float(hr),
                "mrr": float(mrr),
                "precision@5": float(prec),
                "evaluated_queries": evaluated_qs,
                "total_observations": len(sub_df),
            }
            print(f"{config_name:<35} | {rec:<10.4f} | {hr:<12.4f} | {mrr:<8.4f} | {prec:<12.4f} | {evaluated_qs:<12}")

        # 2. Latency Analysis (Separated by Cold vs Warm, Reporting Median and p95)
        CONFIG_NAMES = {
            "A": "Qdrant Vector Only",
            "B": "Hybrid (Qdrant + BM25 + RRF)",
            "C": "Hybrid + Cross-Encoder Rerank",
        }

        print("\n" + "=" * 80)
        print("LATENCY BENCHMARK RESULTS (ms) — WARM RUNS")
        print("=" * 80)
        print(f"{'Config / Stage':<35} | {'N':<5} | {'Median (p50)':<14} | {'p95':<10} | {'Mean':<10} | {'Fail Rate':<10}")
        print("-" * 80)

        warm_df = df[df["run_type"] == "warm"]
        if len(warm_df) == 0:
            if self.iterations < 2:
                print("[Benchmark Note] Benchmark was executed with iterations=1. Only cold-start runs were collected.")
                print("                 Re-run with --iterations >= 2 to collect warm-run latency measurements.\n")
            else:
                print("[Benchmark ERROR] No warm-run samples recorded despite iterations >= 2! Check for execution failures.\n")

        for config_id in ["A", "B", "C"]:
            config_name = CONFIG_NAMES.get(config_id, f"Config {config_id}")
            sub = warm_df[warm_df["config_id"] == config_id]
            n = len(sub)

            if n == 0:
                fail_rate = 100.0 if self.iterations >= 2 else 0.0
                summary["latency"][config_id] = {
                    "config_name": config_name,
                    "warm_samples": 0,
                    "failure_rate_pct": float(fail_rate),
                    "retrieval": {"median_ms": None, "p95_ms": None, "mean_ms": None},
                    "reranking": {"median_ms": None, "p95_ms": None, "mean_ms": None},
                    "total": {"median_ms": None, "p95_ms": None, "mean_ms": None},
                }
                print(f"{config_name + ' [Total]':<35} | {0:<5} | {'N/A':<14} | {'N/A':<10} | {'N/A':<10} | {fail_rate:<10.1f}%")
                continue

            fail_rate = (sub["success"] == False).mean() * 100.0

            # Retrieval Latency
            ret_med = sub["retrieval_latency_ms"].median()
            ret_p95 = sub["retrieval_latency_ms"].quantile(0.95)
            ret_mean = sub["retrieval_latency_ms"].mean()

            # Total Latency
            tot_med = sub["total_latency_ms"].median()
            tot_p95 = sub["total_latency_ms"].quantile(0.95)
            tot_mean = sub["total_latency_ms"].mean()

            # Reranking Latency (for C)
            rerank_med = sub["reranking_latency_ms"].median()
            rerank_p95 = sub["reranking_latency_ms"].quantile(0.95)
            rerank_mean = sub["reranking_latency_ms"].mean()

            summary["latency"][config_id] = {
                "config_name": config_name,
                "warm_samples": n,
                "failure_rate_pct": float(fail_rate),
                "retrieval": {
                    "median_ms": float(ret_med),
                    "p95_ms": float(ret_p95),
                    "mean_ms": float(ret_mean),
                },
                "reranking": {
                    "median_ms": float(rerank_med),
                    "p95_ms": float(rerank_p95),
                    "mean_ms": float(rerank_mean),
                },
                "total": {
                    "median_ms": float(tot_med),
                    "p95_ms": float(tot_p95),
                    "mean_ms": float(tot_mean),
                },
            }

            print(f"{config_name + ' [Total]':<35} | {n:<5} | {tot_med:<14.2f} | {tot_p95:<10.2f} | {tot_mean:<10.2f} | {fail_rate:<10.1f}%")
            if config_id == "C":
                print(f"{'  -> Reranking Stage Only':<35} | {n:<5} | {rerank_med:<14.2f} | {rerank_p95:<10.2f} | {rerank_mean:<10.2f} | {fail_rate:<10.1f}%")

        # 3. Cold Start Latency
        cold_df = df[df["run_type"] == "cold"]
        print("\n" + "=" * 80)
        print("COLD-START VS WARM-RUN COMPARISON (Total ms)")
        print("=" * 80)
        print(f"{'Config':<35} | {'Cold Median':<14} | {'Cold p95':<12} | {'Warm Median':<14} | {'Warm p95':<12}")
        print("-" * 80)

        for config_id in ["A", "B", "C"]:
            config_name = CONFIG_NAMES.get(config_id, f"Config {config_id}")
            c_sub = cold_df[cold_df["config_id"] == config_id]
            w_sub = warm_df[warm_df["config_id"] == config_id]

            if len(c_sub) == 0:
                c_med_str, c_p95_str = "N/A", "N/A"
                c_med, c_p95 = None, None
            else:
                c_med = float(c_sub["total_latency_ms"].median())
                c_p95 = float(c_sub["total_latency_ms"].quantile(0.95))
                c_med_str = f"{c_med:.2f}"
                c_p95_str = f"{c_p95:.2f}"

            if len(w_sub) == 0:
                w_med_str, w_p95_str = "N/A", "N/A"
            else:
                w_med = float(w_sub["total_latency_ms"].median())
                w_p95 = float(w_sub["total_latency_ms"].quantile(0.95))
                w_med_str = f"{w_med:.2f}"
                w_p95_str = f"{w_p95:.2f}"

            summary["latency"][config_id]["cold_start"] = {
                "median_ms": c_med,
                "p95_ms": c_p95,
            }
            print(f"{config_name:<35} | {c_med_str:<14} | {c_p95_str:<12} | {w_med_str:<14} | {w_p95_str:<12}")

        print("=" * 80 + "\n")

        # Save summary JSON
        results_dir = Path(__file__).resolve().parent / "results"
        summary_path = results_dir / "retrieval_benchmark_summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run RAgentic Retrieval & Latency Benchmark")
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
        help="Number of repeated runs per query (default: 3)",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Attempt connecting to live Qdrant/Redis services instead of standalone in-memory",
    )
    args = parser.parse_args()

    runner = RetrievalBenchmarkRunner(
        dataset_path=args.dataset,
        use_live_services=args.live,
        iterations=args.iterations,
    )
    runner.run_benchmark()
