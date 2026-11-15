"""
CLI script to seed synthetic documents into a clean evaluation database and
benchmark Semantic vs Hybrid (BM25 + RRF) vs Hybrid + CrossEncoder Reranking
on the 60-question IT support benchmark dataset.
"""

import json
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.core.database import Base  # noqa: E402
from app.services.embeddings.provider import get_embedding_service  # noqa: E402
from app.services.evaluation.runner import run_retrieval_evaluation  # noqa: E402
from app.services.reranking.cross_encoder import get_reranker  # noqa: E402
from app.services.seed_service import ensure_roles_and_demo_users, seed_sample_documents  # noqa: E402


def main() -> None:
    eval_db_path = REPO_ROOT / "data" / "evaluation" / "eval_benchmark.db"
    if eval_db_path.exists():
        eval_db_path.unlink()

    engine = create_engine(
        f"sqlite+pysqlite:///{eval_db_path}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()

    try:
        users = ensure_roles_and_demo_users(db)
        embedder = get_embedding_service()
        reranker = get_reranker()
        ingested = seed_sample_documents(
            db,
            admin_user_id=users["admin"].id,
            sample_dir=REPO_ROOT / "data" / "sample_documents",
            embedding_service=embedder,
        )
        print(f"Indexed {ingested} documents using embedding model '{embedder.model_name}'.")
        print(f"CrossEncoder reranker '{reranker.model_name}' available: {reranker.is_available}")

        runs = run_retrieval_evaluation(
            db=db,
            modes=["semantic", "hybrid", "hybrid_rerank"],
            k_value=5,
            dataset_path=REPO_ROOT / "data" / "evaluation" / "it_support_benchmark.json",
            embedding_service=embedder,
            reranker=reranker,
        )

        report = []
        for r in runs:
            entry = {
                "retrieval_mode": r.retrieval_mode,
                "question_count": r.question_count,
                "k_value": r.k_value,
                "recall_at_k": r.recall_at_k,
                "precision_at_k": r.precision_at_k,
                "mrr": r.mrr,
                "context_relevance": r.context_relevance,
                "llm_evaluated": r.llm_evaluated,
                "metrics_by_category": r.metrics_by_category,
                "notes": r.notes,
            }
            report.append(entry)
            print(
                f"[{r.retrieval_mode}] Recall@{r.k_value}={r.recall_at_k:.4f} | "
                f"Precision@{r.k_value}={r.precision_at_k:.4f} | "
                f"MRR={r.mrr:.4f} | ContextRel={r.context_relevance:.4f}"
            )

        out_json = REPO_ROOT / "data" / "evaluation" / "benchmark_results.json"
        out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Saved evaluation report to {out_json}")
    finally:
        db.close()
        engine.dispose()
        if eval_db_path.exists():
            try:
                eval_db_path.unlink()
            except OSError:
                pass


if __name__ == "__main__":
    main()

