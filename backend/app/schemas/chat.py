from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class CitationResponse(BaseModel):
    id: str
    document_id: Optional[str]
    chunk_id: Optional[str]
    document_title: str
    original_filename: str
    page_number: Optional[int]
    chunk_index: Optional[int]
    passage_excerpt: str
    relevance_score: float
    rank_order: int


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    rewritten_query: Optional[str] = None
    confidence_score: Optional[float] = None
    evidence_sufficient: Optional[bool] = None
    provider_used: Optional[str] = None
    model_used: Optional[str] = None
    retrieval_latency_ms: Optional[float] = None
    generation_latency_ms: Optional[float] = None
    total_latency_ms: Optional[float] = None
    citations: list[CitationResponse] = []
    created_at: datetime


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    conversation_id: Optional[str] = None
    category_filter: Optional[str] = None
    collection_id: Optional[str] = None
    retrieval_mode: Optional[str] = Field(default="hybrid_rerank", pattern="^(semantic|hybrid|hybrid_rerank)$")


class ChatResponse(BaseModel):
    conversation_id: str
    conversation_title: str
    user_message: MessageResponse
    assistant_message: MessageResponse


class ConversationSummaryResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0
    last_message_preview: Optional[str] = None


class ConversationDetailResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageResponse]


class FeedbackRequest(BaseModel):
    message_id: str
    rating: str = Field(pattern="^(helpful|not_helpful)$")
    comment: Optional[str] = Field(default=None, max_length=1000)


class FeedbackResponse(BaseModel):
    id: str
    message_id: str
    rating: str
    comment: Optional[str]
    created_at: datetime

