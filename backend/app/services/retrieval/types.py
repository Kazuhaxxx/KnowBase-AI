from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    document_title: str
    original_filename: str
    category: str
    department: str
    access_classification: str
    chunk_index: int
    page_number: Optional[int]
    section_heading: Optional[str]
    content: str
    cleaned_content: str
    collection_id: Optional[str] = None
    collection_name: Optional[str] = None
    semantic_score: float = 0.0
    bm25_score: float = 0.0
    rrf_score: float = 0.0
    rerank_score: Optional[float] = None
    final_score: float = 0.0
    retrieval_sources: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

