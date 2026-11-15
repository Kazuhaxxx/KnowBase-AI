# RAG Evaluation Methodology & Benchmark Results

## 1. Benchmark Dataset
- **File**: `data/evaluation/it_support_benchmark.json`
- **Size**: 60 IT support benchmark questions across 10 categories (`Microsoft 365`, `VPN`, `Troubleshooting`, `Hardware`, `Network`, `Account and Access`, `Software`, `IT Policies`, `General IT Support`, plus 3 `Out of Scope` abstention probes).
- **Corpus**: 14 synthetic NovaTech Global documents in `data/sample_documents/`, including 2 deliberately unrelated facilities/HR documents and 2 restricted/IT-only documents.

## 2. Evaluation Metrics
Automated deterministic metrics (`backend/app/services/evaluation/metrics.py`):
- **Recall@5**: Fraction of questions where the ground-truth document appeared in the top-5 retrieved chunks (or correctly abstained for `Out of Scope` items).
- **Precision@5**: Fraction of top-5 retrieved chunks belonging to the ground-truth document.
- **Mean Reciprocal Rank (MRR)**: Average of `1 / rank` of the first matching ground-truth chunk.
- **Context Relevance**: Fraction of expected technical keywords/error codes present in the retrieved top-5 context.

> **Distinction Between Automated and LLM/Human Evaluation:**  
> All metrics reported below were produced deterministically by running `backend/scripts/run_evaluation.py` with `SentenceTransformer("all-MiniLM-L6-v2")` and `CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")`. `faithfulness`, `answer_relevance`, and `citation_correctness` are left `null` (`llm_evaluated: false`) because no live Ollama/Gemini inference daemon was invoked during the retrieval benchmark; no LLM scores were fabricated.

## 3. Observed Benchmark Results (`K = 5`, 60 Questions)

| Configuration | Recall@5 | Precision@5 | MRR | Context Relevance |
| --- | :---: | :---: | :---: | :---: |
| **Semantic Only** (`all-MiniLM-L6-v2`) | 1.0000 | 0.6767 | 0.9917 | 0.9889 |
| **Hybrid** (`Semantic + BM25Plus + RRF`) | 0.9833 | 0.6867 | 0.9750 | 0.9722 |
| **Hybrid + Cross-Encoder Reranking** (`ms-marco-MiniLM-L-6-v2`) | **1.0000** | 0.6400 | **1.0000** | **1.0000** |

### Key Takeaways
1. **Cross-encoder reranking achieved `1.0000` MRR and `1.0000` Context Relevance**, ranking the exact ground-truth document #1 on every in-scope query (`Hardware` MRR improved from `0.9545` to `1.0000`, `VPN` Context Relevance improved from `0.8889` to `1.0000`).
2. **Out-of-Scope Abstention**: Without cross-encoder calibration, `hybrid` passed 1 out-of-scope keyword collision (`0.6667` on Out of Scope). Adding `ms-marco-MiniLM-L-6-v2` logit calibration restored `1.0000` Out-of-Scope abstention accuracy.
3. Full JSON output is stored in `data/evaluation/benchmark_results.json`.

