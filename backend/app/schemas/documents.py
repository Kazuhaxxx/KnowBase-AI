from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class DocumentChunkResponse(BaseModel):
    id: str
    chunk_index: int
    content: str
    cleaned_content: str
    page_number: Optional[int]
    section_heading: Optional[str]
    token_count: int
    char_count: int
    embedding_model: str
    embedding_dim: int
    metadata_json: dict[str, Any]


class DocumentSummaryResponse(BaseModel):
    id: str
    title: str
    original_filename: str
    mime_type: str
    file_size_bytes: int
    file_hash: str
    category: str
    department: str
    access_classification: str
    collection_id: Optional[str] = None
    version: int
    processing_status: str
    error_message: Optional[str]
    page_count: Optional[int]
    chunk_count: int
    created_at: datetime
    last_processed_at: Optional[datetime]


class DocumentDetailResponse(DocumentSummaryResponse):
    extracted_preview: Optional[str]
    chunks: list[DocumentChunkResponse] = []


class DocumentUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=2, max_length=255)
    category: Optional[str] = None
    department: Optional[str] = Field(default=None, min_length=2, max_length=100)
    access_classification: Optional[str] = None
    collection_id: Optional[str] = None


class DocumentUploadResult(BaseModel):
    document: DocumentSummaryResponse
    duplicate_detected: bool = False
    replaced_previous_version: bool = False
    message: str


class KnowledgeSearchHit(BaseModel):
    document_id: str
    document_title: str
    original_filename: str
    category: str
    department: str
    access_classification: str
    page_number: Optional[int]
    chunk_id: str
    chunk_index: int
    excerpt: str
    score: float

