from typing import Optional

import numpy as np
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk
from app.services.embeddings.provider import EmbeddingService, get_embedding_service
from app.services.retrieval.types import RetrievedChunk


def semantic_retrieve(
    db: Session,
    query: str,
    allowed_classifications: list[str],
    top_k: int = 12,
    category_filter: Optional[str] = None,
    collection_id: Optional[str] = None,
    embedding_service: Optional[EmbeddingService] = None,
) -> list[RetrievedChunk]:
    """
    Perform RBAC-filtered semantic vector similarity retrieval.
    Uses native pgvector cosine distance on PostgreSQL and normalized cosine similarity on SQLite.
    """
    if not allowed_classifications:
        return []

    embedder = embedding_service or get_embedding_service()
    query_vec = embedder.encode_query(query)
    dialect = db.bind.dialect.name if db.bind else "unknown"

    base_query = (
        db.query(DocumentChunk, Document)
        .join(Document, DocumentChunk.document_id == Document.id)
        .filter(
            Document.processing_status == "indexed",
            Document.access_classification.in_(allowed_classifications),
            DocumentChunk.embedding.isnot(None),
        )
    )
    if category_filter:
        base_query = base_query.filter(Document.category == category_filter)
    if collection_id:
        base_query = base_query.filter(Document.collection_id == collection_id)

    if dialect == "postgresql":
        distance_expr = DocumentChunk.embedding.cosine_distance(query_vec)
        rows = (
            base_query.add_columns(distance_expr.label("distance"))
            .order_by(distance_expr.asc())
            .limit(top_k)
            .all()
        )
        results: list[RetrievedChunk] = []
        for chunk, doc, distance in rows:
            sim = max(0.0, min(1.0, 1.0 - float(distance)))
            results.append(_to_retrieved_chunk(chunk, doc, semantic_score=sim))
        return results

    # Portable cosine similarity for SQLite unit tests
    q_arr = np.asarray(query_vec, dtype=np.float32)
    q_norm = float(np.linalg.norm(q_arr))
    if q_norm == 0:
        return []
    q_arr = q_arr / q_norm

    rows = base_query.all()
    scored: list[tuple[float, DocumentChunk, Document]] = []
    for chunk, doc in rows:
        if not chunk.embedding:
            continue
        c_arr = np.asarray(chunk.embedding, dtype=np.float32)
        c_norm = float(np.linalg.norm(c_arr))
        if c_norm == 0:
            continue
        sim = float(np.dot(q_arr, c_arr / c_norm))
        scored.append((max(0.0, sim), chunk, doc))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [_to_retrieved_chunk(chunk, doc, semantic_score=score) for score, chunk, doc in scored[:top_k]]


def _to_retrieved_chunk(chunk: DocumentChunk, doc: Document, semantic_score: float) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk.id,
        document_id=doc.id,
        document_title=doc.title,
        original_filename=doc.original_filename,
        category=doc.category,
        department=doc.department,
        access_classification=doc.access_classification,
        chunk_index=chunk.chunk_index,
        page_number=chunk.page_number,
        section_heading=chunk.section_heading,
        content=chunk.content,
        cleaned_content=chunk.cleaned_content,
        collection_id=doc.collection_id,
        semantic_score=round(semantic_score, 6),
        final_score=round(semantic_score, 6),
        retrieval_sources=["semantic"],
        metadata=dict(chunk.metadata_json or {}),
    )

