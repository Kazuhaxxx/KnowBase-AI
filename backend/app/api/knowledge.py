from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.security import get_allowed_classifications
from app.models.document import Document
from app.models.user import User
from app.schemas.documents import (
    DocumentChunkResponse,
    DocumentDetailResponse,
    DocumentSummaryResponse,
    KnowledgeSearchHit,
)
from app.services.retrieval.hybrid import hybrid_retrieve

router = APIRouter(prefix="/knowledge", tags=["Knowledge Explorer"])


@router.get("/documents", response_model=list[DocumentSummaryResponse])
def browse_accessible_documents(
    category: Optional[str] = None,
    collection_id: Optional[str] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DocumentSummaryResponse]:
    """List knowledge base articles filtered strictly by the authenticated user's role."""
    allowed = get_allowed_classifications(current_user.role.name)
    query = (
        db.query(Document)
        .filter(
            Document.processing_status == "indexed",
            Document.access_classification.in_(allowed),
        )
        .order_by(Document.last_processed_at.desc(), Document.created_at.desc())
    )
    if category:
        query = query.filter(Document.category == category)
    if collection_id:
        query = query.filter(Document.collection_id == collection_id)
    if q and q.strip():
        like_term = f"%{q.strip()}%"
        query = query.filter(
            (Document.title.ilike(like_term)) | (Document.extracted_preview.ilike(like_term))
        )

    docs = query.all()
    return [
        DocumentSummaryResponse(
            id=d.id,
            title=d.title,
            original_filename=d.original_filename,
            mime_type=d.mime_type,
            file_size_bytes=d.file_size_bytes,
            file_hash=d.file_hash,
            category=d.category,
            department=d.department,
            access_classification=d.access_classification,
            collection_id=d.collection_id,
            version=d.version,
            processing_status=d.processing_status,
            error_message=d.error_message,
            page_count=d.page_count,
            chunk_count=d.chunk_count,
            created_at=d.created_at,
            last_processed_at=d.last_processed_at,
        )
        for d in docs
    ]


@router.get("/search", response_model=list[KnowledgeSearchHit])
def search_knowledge(
    q: str = Query(min_length=2, max_length=300),
    category: Optional[str] = None,
    collection_id: Optional[str] = None,
    limit: int = Query(default=8, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[KnowledgeSearchHit]:
    """Perform hybrid search over RBAC-authorized documents."""
    allowed = get_allowed_classifications(current_user.role.name)
    hits = hybrid_retrieve(
        db=db,
        query=q,
        allowed_classifications=allowed,
        mode="hybrid",
        top_n=limit,
        category_filter=category,
        collection_id=collection_id,
    )
    return [
        KnowledgeSearchHit(
            document_id=h.document_id,
            document_title=h.document_title,
            original_filename=h.original_filename,
            category=h.category,
            department=h.department,
            access_classification=h.access_classification,
            page_number=h.page_number,
            chunk_id=h.chunk_id,
            chunk_index=h.chunk_index,
            excerpt=h.cleaned_content[:450],
            score=h.final_score,
        )
        for h in hits
    ]


@router.get("/documents/{document_id}", response_model=DocumentDetailResponse)
def get_accessible_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentDetailResponse:
    """Inspect a single document only if the authenticated user is authorized to access it."""
    allowed = get_allowed_classifications(current_user.role.name)
    doc = (
        db.query(Document)
        .options(joinedload(Document.chunks))
        .filter(
            Document.id == document_id,
            Document.processing_status == "indexed",
            Document.access_classification.in_(allowed),
        )
        .first()
    )
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found or access denied.")

    return DocumentDetailResponse(
        id=doc.id,
        title=doc.title,
        original_filename=doc.original_filename,
        mime_type=doc.mime_type,
        file_size_bytes=doc.file_size_bytes,
        file_hash=doc.file_hash,
        category=doc.category,
        department=doc.department,
        access_classification=doc.access_classification,
        collection_id=doc.collection_id,
        version=doc.version,
        processing_status=doc.processing_status,
        error_message=doc.error_message,
        page_count=doc.page_count,
        chunk_count=doc.chunk_count,
        created_at=doc.created_at,
        last_processed_at=doc.last_processed_at,
        extracted_preview=doc.extracted_preview,
        chunks=[
            DocumentChunkResponse(
                id=c.id,
                chunk_index=c.chunk_index,
                content=c.content,
                cleaned_content=c.cleaned_content,
                page_number=c.page_number,
                section_heading=c.section_heading,
                token_count=c.token_count,
                char_count=c.char_count,
                embedding_model=c.embedding_model,
                embedding_dim=c.embedding_dim,
                metadata_json=c.metadata_json,
            )
            for c in doc.chunks
        ],
    )

