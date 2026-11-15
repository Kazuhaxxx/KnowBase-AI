from collections import Counter

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.api.deps import require_admin
from app.core.config import get_settings
from app.core.database import check_database_health, get_db
from app.models.chat import Conversation, Feedback, Message
from app.models.document import Document, DocumentChunk
from app.models.evaluation import EvaluationRun, QueryTelemetry
from app.models.user import Role, User
from app.schemas.admin import (
    AdminOverviewResponse,
    AdminUserItem,
    AdminUserUpdateRequest,
    AnalyticsResponse,
    EvaluationRunRequest,
    EvaluationRunResponse,
    SystemConfigResponse,
)
from app.services.evaluation.runner import run_retrieval_evaluation
from app.services.generation.providers import OllamaProvider

router = APIRouter(prefix="/admin", tags=["Administration & Evaluation"])


@router.get("/overview", response_model=AdminOverviewResponse)
def get_admin_overview(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> AdminOverviewResponse:
    total_docs = db.query(func.count(Document.id)).scalar() or 0
    indexed_docs = (
        db.query(func.count(Document.id))
        .filter(Document.processing_status == "indexed")
        .scalar()
        or 0
    )
    failed_docs = (
        db.query(func.count(Document.id))
        .filter(Document.processing_status == "failed")
        .scalar()
        or 0
    )
    pending_docs = (
        db.query(func.count(Document.id))
        .filter(Document.processing_status.in_(["pending", "processing"]))
        .scalar()
        or 0
    )
    total_chunks = db.query(func.count(DocumentChunk.id)).scalar() or 0
    total_convs = db.query(func.count(Conversation.id)).scalar() or 0
    total_questions = (
        db.query(func.count(Message.id)).filter(Message.role == "user").scalar() or 0
    )
    helpful = (
        db.query(func.count(Feedback.id)).filter(Feedback.rating == "helpful").scalar() or 0
    )
    not_helpful = (
        db.query(func.count(Feedback.id)).filter(Feedback.rating == "not_helpful").scalar() or 0
    )

    telemetry_rows = db.query(QueryTelemetry.category).all()
    cat_counts = Counter(row[0] or "General" for row in telemetry_rows)
    top_categories = [
        {"category": cat, "count": count} for cat, count in cat_counts.most_common(6)
    ]

    recent_docs = (
        db.query(Document).order_by(Document.created_at.desc()).limit(5).all()
    )
    return AdminOverviewResponse(
        total_documents=total_docs,
        indexed_documents=indexed_docs,
        failed_documents=failed_docs,
        pending_documents=pending_docs,
        total_chunks=total_chunks,
        total_conversations=total_convs,
        total_questions=total_questions,
        helpful_feedback=helpful,
        not_helpful_feedback=not_helpful,
        top_categories=top_categories,
        recent_documents=[
            {
                "id": d.id,
                "title": d.title,
                "category": d.category,
                "status": d.processing_status,
                "classification": d.access_classification,
                "chunk_count": d.chunk_count,
                "created_at": d.created_at,
            }
            for d in recent_docs
        ],
    )


@router.get("/analytics", response_model=AnalyticsResponse)
def get_analytics(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> AnalyticsResponse:
    """Return non-sensitive aggregate usage, latency, feedback, and retrieval telemetry."""
    telemetry = db.query(QueryTelemetry).order_by(QueryTelemetry.created_at.asc()).all()
    total_questions = len(telemetry)
    total_conversations = db.query(func.count(Conversation.id)).scalar() or 0

    if total_questions > 0:
        avg_total = round(sum(t.total_latency_ms for t in telemetry) / total_questions, 2)
        avg_ret = round(sum(t.retrieval_latency_ms for t in telemetry) / total_questions, 2)
        avg_gen = round(sum(t.generation_latency_ms for t in telemetry) / total_questions, 2)
        sufficient_count = sum(1 for t in telemetry if t.evidence_sufficient)
        sufficiency_rate = round(sufficient_count / total_questions, 4)
        failed_retrieval_count = total_questions - sufficient_count
    else:
        avg_total = avg_ret = avg_gen = sufficiency_rate = 0.0
        failed_retrieval_count = 0

    helpful = db.query(func.count(Feedback.id)).filter(Feedback.rating == "helpful").scalar() or 0
    not_helpful = (
        db.query(func.count(Feedback.id)).filter(Feedback.rating == "not_helpful").scalar() or 0
    )

    doc_counter: Counter[str] = Counter()
    cat_counter: Counter[str] = Counter()
    for t in telemetry:
        cat_counter[t.category or "Uncategorized"] += 1
        for doc_id in t.retrieved_document_ids or []:
            doc_counter[doc_id] += 1

    top_doc_ids = [doc_id for doc_id, _ in doc_counter.most_common(6)]
    doc_titles = (
        {
            d.id: d.title
            for d in db.query(Document).filter(Document.id.in_(top_doc_ids)).all()
        }
        if top_doc_ids
        else {}
    )

    freq_docs = [
        {"document_id": doc_id, "title": doc_titles.get(doc_id, "Deleted Document"), "count": count}
        for doc_id, count in doc_counter.most_common(6)
    ]

    category_breakdown = [
        {"category": cat, "count": count} for cat, count in cat_counter.most_common(10)
    ]

    latency_trend = [
        {
            "index": idx + 1,
            "retrieval_ms": t.retrieval_latency_ms,
            "generation_ms": t.generation_latency_ms,
            "total_ms": t.total_latency_ms,
            "sufficient": t.evidence_sufficient,
        }
        for idx, t in enumerate(telemetry[-20:])
    ]

    return AnalyticsResponse(
        total_questions=total_questions,
        total_conversations=total_conversations,
        avg_total_latency_ms=avg_total,
        avg_retrieval_latency_ms=avg_ret,
        avg_generation_latency_ms=avg_gen,
        evidence_sufficiency_rate=sufficiency_rate,
        failed_retrieval_count=failed_retrieval_count,
        helpful_feedback=helpful,
        not_helpful_feedback=not_helpful,
        frequently_retrieved_documents=freq_docs,
        category_breakdown=category_breakdown,
        latency_trend=latency_trend,
    )


@router.get("/users", response_model=list[AdminUserItem])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[AdminUserItem]:
    users = db.query(User).options(joinedload(User.role)).order_by(User.created_at.asc()).all()
    return [
        AdminUserItem(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            department=u.department,
            role=u.role.name,
            is_active=u.is_active,
            created_at=u.created_at,
        )
        for u in users
    ]


@router.patch("/users/{user_id}", response_model=AdminUserItem)
def update_user(
    user_id: str,
    payload: AdminUserUpdateRequest,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
) -> AdminUserItem:
    target = db.query(User).options(joinedload(User.role)).filter(User.id == user_id).first()
    if target is None:
        raise HTTPException(status_code=404, detail="User not found.")

    if target.id == admin_user.id and payload.is_active is False:
        raise HTTPException(status_code=400, detail="Administrators cannot deactivate themselves.")

    if payload.role is not None:
        role_obj = db.query(Role).filter(Role.name == payload.role).first()
        if role_obj is None:
            raise HTTPException(status_code=400, detail="Unknown role.")
        target.role_id = role_obj.id
    if payload.is_active is not None:
        target.is_active = payload.is_active
    if payload.department is not None:
        target.department = payload.department.strip()

    db.commit()
    db.refresh(target)
    refreshed = db.query(User).options(joinedload(User.role)).filter(User.id == target.id).one()
    return AdminUserItem(
        id=refreshed.id,
        email=refreshed.email,
        full_name=refreshed.full_name,
        department=refreshed.department,
        role=refreshed.role.name,
        is_active=refreshed.is_active,
        created_at=refreshed.created_at,
    )


@router.get("/config", response_model=SystemConfigResponse)
async def get_system_config(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> SystemConfigResponse:
    """Display active AI execution mode and RAG parameters without exposing secrets."""
    settings = get_settings()
    db_status = check_database_health(db)
    ollama_available, ollama_models = await OllamaProvider.check_availability(
        settings.ollama_base_url
    )

    active_provider = "ollama" if settings.ai_execution_mode == "local" else "gemini"
    active_model = (
        settings.ollama_model
        if settings.ai_execution_mode == "local"
        else settings.gemini_model
    )

    return SystemConfigResponse(
        ai_execution_mode=settings.ai_execution_mode,
        active_provider=active_provider,
        active_model=active_model,
        ollama_base_url=settings.ollama_base_url,
        ollama_available=ollama_available,
        ollama_models_installed=ollama_models,
        gemini_configured=bool(settings.gemini_api_key),
        gemini_model=settings.gemini_model,
        embedding_model=settings.embedding_model,
        embedding_dim=settings.embedding_dim,
        reranker_model=settings.reranker_model,
        enable_reranking=settings.enable_reranking,
        enable_query_rewriting=settings.enable_query_rewriting,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        rrf_k=settings.rrf_k,
        semantic_weight=settings.semantic_weight,
        bm25_weight=settings.bm25_weight,
        retrieval_top_n_final=settings.retrieval_top_n_final,
        database_status=db_status,
        security_notice=(
            "Demonstration environment: Synthetic knowledge documents and sample accounts are active. "
            "Do not upload real confidential credentials or production PII without an independent security audit."
        ),
    )


@router.post("/evaluation/run", response_model=list[EvaluationRunResponse])
def trigger_evaluation(
    payload: EvaluationRunRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[EvaluationRunResponse]:
    """Run the benchmark evaluation suite across requested retrieval configurations."""
    try:
        runs = run_retrieval_evaluation(
            db=db,
            modes=payload.modes,
            k_value=payload.k_value,
            max_questions=payload.max_questions,
        )
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return [_serialize_eval_run(r) for r in runs]


@router.get("/evaluation/results", response_model=list[EvaluationRunResponse])
def list_evaluation_results(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[EvaluationRunResponse]:
    runs = db.query(EvaluationRun).order_by(EvaluationRun.created_at.desc()).limit(25).all()
    return [_serialize_eval_run(r) for r in runs]


def _serialize_eval_run(run: EvaluationRun) -> EvaluationRunResponse:
    return EvaluationRunResponse(
        id=run.id,
        run_name=run.run_name,
        retrieval_mode=run.retrieval_mode,
        dataset_name=run.dataset_name,
        question_count=run.question_count,
        k_value=run.k_value,
        recall_at_k=run.recall_at_k,
        precision_at_k=run.precision_at_k,
        mrr=run.mrr,
        context_relevance=run.context_relevance,
        faithfulness=run.faithfulness,
        answer_relevance=run.answer_relevance,
        citation_correctness=run.citation_correctness,
        llm_evaluated=run.llm_evaluated,
        metrics_by_category=run.metrics_by_category,
        notes=run.notes,
        created_at=run.created_at,
    )

