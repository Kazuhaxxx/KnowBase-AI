import json
from pathlib import Path
import time
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.evaluation import EvaluationRecord, EvaluationRun
from app.services.embeddings.provider import EmbeddingService
from app.services.evaluation.metrics import compute_retrieval_metrics
from app.services.generation.evidence import assess_evidence_sufficiency
from app.services.reranking.cross_encoder import CrossEncoderReranker, get_reranker
from app.services.retrieval.hybrid import hybrid_retrieve
from app.services.retrieval.query_rewriter import rewrite_query


DEFAULT_DATASET_PATH = (
    Path(__file__).resolve().parents[4] / "data" / "evaluation" / "it_support_benchmark.json"
)


def load_benchmark_dataset(dataset_path: Optional[Path] = None) -> list[dict[str, Any]]:
    path = dataset_path or DEFAULT_DATASET_PATH
    if not path.exists():
        raise FileNotFoundError(f"Benchmark dataset not found at {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Benchmark dataset must be a JSON array.")
    return data


def run_retrieval_evaluation(
    db: Session,
    modes: list[str],
    k_value: int = 5,
    max_questions: Optional[int] = None,
    dataset_path: Optional[Path] = None,
    embedding_service: Optional[EmbeddingService] = None,
    reranker: Optional[CrossEncoderReranker] = None,
) -> list[EvaluationRun]:
    """
    Execute deterministic retrieval evaluation across specified retrieval modes
    ('semantic', 'hybrid', 'hybrid_rerank') and persist results in PostgreSQL/SQLite.
    """
    dataset = load_benchmark_dataset(dataset_path)
    if max_questions is not None:
        dataset = dataset[:max_questions]

    active_reranker = reranker or get_reranker()
    # Evaluate with admin-level visibility so restricted/IT-only benchmark items can be tested too
    eval_classifications = ["public", "employee", "it_only", "restricted"]

    runs: list[EvaluationRun] = []
    for mode in modes:
        if mode not in {"semantic", "hybrid", "hybrid_rerank"}:
            raise ValueError(f"Unsupported evaluation retrieval mode: {mode}")

        recalls: list[float] = []
        precisions: list[float] = []
        rrs: list[float] = []
        ctx_rels: list[float] = []
        by_category: dict[str, dict[str, list[float]]] = {}
        record_models: list[EvaluationRecord] = []

        for item in dataset:
            qid = item["id"]
            category = item["category"]
            question = item["question"]
            expected_doc = item["expected_document"]
            expected_keywords = item.get("expected_keywords", [])

            start = time.perf_counter()
            rewritten = rewrite_query(question, enabled=True)
            candidates = hybrid_retrieve(
                db=db,
                query=rewritten,
                allowed_classifications=eval_classifications,
                mode=mode,
                top_n=max(k_value, 10),
                embedding_service=embedding_service,
            )

            rerank_status = "none"
            if mode == "hybrid_rerank" and candidates:
                ranked, rerank_status = active_reranker.rerank(
                    query=question, candidates=candidates, top_n=k_value
                )
            else:
                ranked = candidates[:k_value]

            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            assessment = assess_evidence_sufficiency(question, ranked)

            recall, precision, rr, ctx_rel = compute_retrieval_metrics(
                expected_document=expected_doc,
                expected_keywords=expected_keywords,
                retrieved_chunks=ranked,
                k=k_value,
                evidence_sufficient=assessment.sufficient,
            )

            recalls.append(recall)
            precisions.append(precision)
            rrs.append(rr)
            ctx_rels.append(ctx_rel)

            cat_bucket = by_category.setdefault(
                category, {"recall": [], "precision": [], "mrr": [], "context_relevance": []}
            )
            cat_bucket["recall"].append(recall)
            cat_bucket["precision"].append(precision)
            cat_bucket["mrr"].append(rr)
            cat_bucket["context_relevance"].append(ctx_rel)

            retrieved_doc_names = list(
                dict.fromkeys(c.original_filename for c in ranked[:k_value])
            )
            record_models.append(
                EvaluationRecord(
                    question_id=qid,
                    category=category,
                    question=question,
                    expected_document=expected_doc,
                    retrieved_documents=retrieved_doc_names,
                    recall_at_k=recall,
                    precision_at_k=precision,
                    reciprocal_rank=rr,
                    context_relevance=ctx_rel,
                    latency_ms=latency_ms,
                )
            )

        n = max(1, len(dataset))
        summarized_categories = {
            cat: {
                "count": len(vals["recall"]),
                "recall_at_k": round(sum(vals["recall"]) / len(vals["recall"]), 4),
                "precision_at_k": round(sum(vals["precision"]) / len(vals["precision"]), 4),
                "mrr": round(sum(vals["mrr"]) / len(vals["mrr"]), 4),
                "context_relevance": round(
                    sum(vals["context_relevance"]) / len(vals["context_relevance"]), 4
                ),
            }
            for cat, vals in by_category.items()
        }

        notes = (
            f"Automated deterministic retrieval evaluation on {len(dataset)} benchmark questions "
            f"(K={k_value}). LLM-as-judge metrics omitted because live LLM evaluation was not requested."
        )
        if mode == "hybrid_rerank" and not active_reranker.is_available:
            notes += " CrossEncoder fallback to RRF was active."

        run = EvaluationRun(
            run_name=f"Benchmark ({mode})",
            retrieval_mode=mode,
            dataset_name="it_support_benchmark.json",
            question_count=len(dataset),
            k_value=k_value,
            recall_at_k=round(sum(recalls) / n, 4),
            precision_at_k=round(sum(precisions) / n, 4),
            mrr=round(sum(rrs) / n, 4),
            context_relevance=round(sum(ctx_rels) / n, 4),
            faithfulness=None,
            answer_relevance=None,
            citation_correctness=None,
            llm_evaluated=False,
            metrics_by_category=summarized_categories,
            notes=notes,
        )
        db.add(run)
        db.flush()

        for rec in record_models:
            rec.run_id = run.id
            db.add(rec)

        db.commit()
        db.refresh(run)
        runs.append(run)

    return runs

