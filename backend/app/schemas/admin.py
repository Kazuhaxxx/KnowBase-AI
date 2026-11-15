from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class AdminUserUpdateRequest(BaseModel):
    role: Optional[str] = Field(default=None, pattern="^(employee|it_staff|admin)$")
    is_active: Optional[bool] = None
    department: Optional[str] = Field(default=None, min_length=2, max_length=100)


class AdminUserItem(BaseModel):
    id: str
    email: str
    full_name: str
    department: str
    role: str
    is_active: bool
    created_at: datetime


class AdminOverviewResponse(BaseModel):
    total_documents: int
    indexed_documents: int
    failed_documents: int
    pending_documents: int
    total_chunks: int
    total_conversations: int
    total_questions: int
    helpful_feedback: int
    not_helpful_feedback: int
    top_categories: list[dict[str, Any]]
    recent_documents: list[dict[str, Any]]


class AnalyticsResponse(BaseModel):
    total_questions: int
    total_conversations: int
    avg_total_latency_ms: float
    avg_retrieval_latency_ms: float
    avg_generation_latency_ms: float
    evidence_sufficiency_rate: float
    failed_retrieval_count: int
    helpful_feedback: int
    not_helpful_feedback: int
    frequently_retrieved_documents: list[dict[str, Any]]
    category_breakdown: list[dict[str, Any]]
    latency_trend: list[dict[str, Any]]


class SystemConfigResponse(BaseModel):
    ai_execution_mode: str
    active_provider: str
    active_model: str
    ollama_base_url: str
    ollama_available: bool
    ollama_models_installed: list[str]
    gemini_configured: bool
    gemini_model: str
    embedding_model: str
    embedding_dim: int
    reranker_model: str
    enable_reranking: bool
    enable_query_rewriting: bool
    chunk_size: int
    chunk_overlap: int
    rrf_k: int
    semantic_weight: float
    bm25_weight: float
    retrieval_top_n_final: int
    database_status: dict[str, Any]
    security_notice: str


class EvaluationRunRequest(BaseModel):
    modes: list[str] = Field(default=["semantic", "hybrid", "hybrid_rerank"])
    k_value: int = Field(default=5, ge=1, le=20)
    run_llm_judge: bool = False
    max_questions: Optional[int] = Field(default=None, ge=5, le=200)


class EvaluationRunResponse(BaseModel):
    id: str
    run_name: str
    retrieval_mode: str
    dataset_name: str
    question_count: int
    k_value: int
    recall_at_k: float
    precision_at_k: float
    mrr: float
    context_relevance: float
    faithfulness: Optional[float]
    answer_relevance: Optional[float]
    citation_correctness: Optional[float]
    llm_evaluated: bool
    metrics_by_category: dict[str, Any]
    notes: str
    created_at: datetime

