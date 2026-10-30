# RAgentic Benchmark Suite

A reproducible benchmark suite for evaluating retrieval quality, latency profiles, and LLM response fidelity across RAgentic's multi-stage RAG architecture.

---

## 1. Supported Configurations

The suite measures the exact retrieval pipelines implemented in `app/services/retrieval/`:

- **Configuration A: Qdrant-Only Dense Retrieval**
  - Query vector generated via `all-MiniLM-L6-v2` (`embed_query`).
  - Approximate Nearest Neighbor (ANN) cosine similarity search in Qdrant.
- **Configuration B: Hybrid Retrieval (Qdrant + BM25 + RRF)**
  - Concurrent dense search and lexical search (`BM25Okapi`).
  - Reciprocal Rank Fusion ($k=60$) with query-adaptive weights from `router.py`.
- **Configuration C: Hybrid Retrieval + Cross-Encoder Reranking**
  - High-recall candidates merged via RRF.
  - Full cross-attention reranking via `cross-encoder/ms-marco-MiniLM-L-6-v2`.
  - Sigmoid score normalization and threshold filtering ($0.3$).

---

## 2. Evaluation Metrics

### Retrieval Quality
- **Recall@5**: Proportion of available relevant chunks captured in the top-5 results ($\frac{|\text{Retrieved} \cap \text{Relevant}|}{\min(|\text{Relevant}|, 5)}$).
- **Hit-Rate@5**: Percentage of queries with at least one relevant chunk in the top-5 retrieved items.
- **Mean Reciprocal Rank (MRR)**: Average reciprocal rank ($\frac{1}{\text{rank}}$) of the first relevant chunk ($0$ if none in top-5).
- **Precision@5**: Proportion of retrieved top-5 chunks that are genuinely relevant ($\frac{|\text{Retrieved} \cap \text{Relevant}|}{5}$).

### Latency Profiles
- Measured using high-resolution monotonic clocks (`time.perf_counter()`).
- Repeated across configurable trials (default: 3 iterations = 60 trials per configuration).
- Reports: Sample count ($N$), Mean, Median ($p_{50}$), $p_{95}$, Min, Max, and Failure Rate ($\%$).
- Distinguishes **Cold-Start** (first inference pass) from **Warm-Run** steady-state execution.
- Disaggregates **Retrieval Latency** from **Reranking Latency**.

### LLM Response Quality (via `evaluate_response`)
- **Faithfulness**: Are claims in the generated response supported by retrieved contexts?
- **Context Precision**: Relevance of retrieved chunks to the question asked.
- **Answer Relevance**: Does the generated answer address the user query?
- **Time-to-First-Token (TTFT)**: Perceived latency from request start until first stream token.

---

## 3. Directory Layout

```
benchmarks/
├── data/
│   ├── dataset_template.json     # JSON schema template for adding custom eval sets
│   └── benchmark_dataset.json    # 12 documents, 20 verified questions with relevance labels
├── results/                      # Output directory for raw CSV and JSON results
│   ├── retrieval_benchmark_raw.csv
│   ├── retrieval_benchmark_raw.json
│   └── retrieval_benchmark_summary.json
├── benchmark_retrieval.py        # Retrieval quality and latency benchmarking script
├── benchmark_quality.py          # Response generation, TTFT, and evaluator script
├── run_all_benchmarks.py         # Unified runner orchestrating all benchmarks
└── README.md                     # Documentation and execution instructions
```

---

## 4. How to Run Locally

### Prerequisites
Activate the project's virtual environment:
```powershell
& "f:\SNine\ragentic\backend\.venv\Scripts\Activate.ps1"
```

### Running Retrieval & Latency Benchmarks (Zero Paid API Calls)
Runs entirely on CPU using local embeddings and reranking. Supports in-memory standalone mode or live Qdrant/Redis services:

```powershell
# Default: Standalone in-memory Qdrant + BM25 (reproducible anywhere without Docker)
& "f:\SNine\ragentic\backend\.venv\Scripts\python.exe" "benchmarks/benchmark_retrieval.py" --iterations 3

# With live Qdrant and Redis services (when Docker containers are running):
& "f:\SNine\ragentic\backend\.venv\Scripts\python.exe" "benchmarks/benchmark_retrieval.py" --live --iterations 3
```

### Running LLM Quality & TTFT Benchmarks
To run the LLM response generation and evaluator benchmark (requires valid `GEMINI_API_KEY` or `OPENROUTER_API_KEY`):

```powershell
# Dry run (verifies prompt construction and evaluator schema without calling APIs):
& "f:\SNine\ragentic\backend\.venv\Scripts\python.exe" "benchmarks/benchmark_quality.py"

# Live evaluation (executes LLM calls across a sample of questions):
& "f:\SNine\ragentic\backend\.venv\Scripts\python.exe" "benchmarks/benchmark_quality.py" --enable-llm --samples 5
```

### Running the Complete Unified Suite
```powershell
& "f:\SNine\ragentic\backend\.venv\Scripts\python.exe" "benchmarks/run_all_benchmarks.py" --iterations 3
```
