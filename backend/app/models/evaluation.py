from datetime import datetime, timezone
from typing import Any, Optional
import uuid

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class QueryTelemetry(Base):
    """Non-sensitive query telemetry (stores no prompt text or chunk contents)."""

    __tablename__ = "query_telemetry"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    retrieval_mode: Mapped[str] = mapped_column(String(40), nullable=False)
    evidence_sufficient: Mapped[bool] = mapped_column(Boolean, nullable=False)
    top_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    retrieval_latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    generation_latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    total_latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    retrieved_document_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    run_name: Mapped[str] = mapped_column(String(150), nullable=False)
    retrieval_mode: Mapped[str] = mapped_column(String(40), nullable=False)
    dataset_name: Mapped[str] = mapped_column(String(150), nullable=False)
    question_count: Mapped[int] = mapped_column(Integer, nullable=False)
    k_value: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    recall_at_k: Mapped[float] = mapped_column(Float, nullable=False)
    precision_at_k: Mapped[float] = mapped_column(Float, nullable=False)
    mrr: Mapped[float] = mapped_column(Float, nullable=False)
    context_relevance: Mapped[float] = mapped_column(Float, nullable=False)
    faithfulness: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    answer_relevance: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    citation_correctness: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    llm_evaluated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    metrics_by_category: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    records: Mapped[list["EvaluationRecord"]] = relationship(
        "EvaluationRecord", back_populates="run", cascade="all, delete-orphan"
    )


class EvaluationRecord(Base):
    __tablename__ = "evaluation_records"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    run_id: Mapped[str] = mapped_column(
        ForeignKey("evaluation_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    expected_document: Mapped[str] = mapped_column(String(255), nullable=False)
    retrieved_documents: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    recall_at_k: Mapped[float] = mapped_column(Float, nullable=False)
    precision_at_k: Mapped[float] = mapped_column(Float, nullable=False)
    reciprocal_rank: Mapped[float] = mapped_column(Float, nullable=False)
    context_relevance: Mapped[float] = mapped_column(Float, nullable=False)
    faithfulness: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    answer_relevance: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    citation_correctness: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False)

    run: Mapped["EvaluationRun"] = relationship("EvaluationRun", back_populates="records")

