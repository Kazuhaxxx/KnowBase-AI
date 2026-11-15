from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import require_admin
from app.core.config import ACCESS_CLASSIFICATIONS, DOCUMENT_CATEGORIES
from app.core.database import get_db
from app.models.document import Document
from app.models.user import User
from app.schemas.documents import (
    DocumentChunkResponse,
    DocumentDetailResponse,
    DocumentSummaryResponse,
    DocumentUpdateRequest,
    DocumentUploadResult,
)
from app.services.ingestion.extractors import DocumentExtractionError
from app.services.ingestion.pipeline import ingest_uploaded_document, reprocess_document

router = APIRouter(prefix="/documents", tags=["Documents (Admin)"])


def _serialize_doc_summary(doc: Document) -> DocumentSummaryResponse:
    return DocumentSummaryResponse(
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
    )


@router.post(
    "/upload",
    response_model=list[DocumentUploadResult],
    status_code=status.HTTP_201_CREATED,
)
async def upload_documents(
    files: list[UploadFile] = File(...),
    category: str = Form("General Knowledge"),
    department: str = Form("General"),
    access_classification: str = Form("employee"),
    collection_id: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
) -> list[DocumentUploadResult]:
    """Upload and ingest one or multiple documents (PDF, DOCX, TXT, MD)."""
    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required.")

    results: list[DocumentUploadResult] = []
    for idx, upload in enumerate(files):
        raw_bytes = await upload.read()
        doc_title = title if (title and len(files) == 1) else None
        try:
            outcome = ingest_uploaded_document(
                db=db,
                filename=upload.filename or f"upload_{idx}.txt",
                content=raw_bytes,
                title=doc_title,
                category=category,
                department=department,
                access_classification=access_classification,
                uploaded_by_user_id=admin_user.id,
                collection_id=collection_id,
            )
            results.append(
                DocumentUploadResult(
                    document=_serialize_doc_summary(outcome.document),
                    duplicate_detected=outcome.duplicate_detected,
                    replaced_previous_version=outcome.replaced_previous_version,
                    message=outcome.message,
                )
            )
        except DocumentExtractionError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return results


@router.get("", response_model=list[DocumentSummaryResponse])
def list_documents(
    category: Optional[str] = None,
    collection_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[DocumentSummaryResponse]:
    """List all knowledge base documents for administrators."""
    query = db.query(Document).order_by(Document.created_at.desc())
    if category:
        query = query.filter(Document.category == category)
    if collection_id:
        query = query.filter(Document.collection_id == collection_id)
    if status_filter:
        query = query.filter(Document.processing_status == status_filter)
    docs = query.all()
    return [_serialize_doc_summary(d) for d in docs]


@router.get("/{document_id}", response_model=DocumentDetailResponse)
def get_document_detail(
    document_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> DocumentDetailResponse:
    """Get document metadata, extracted text preview, and indexed chunks."""
    doc = (
        db.query(Document)
        .options(joinedload(Document.chunks))
        .filter(Document.id == document_id)
        .first()
    )
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    summary = _serialize_doc_summary(doc)
    return DocumentDetailResponse(
        **summary.model_dump(),
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


@router.patch("/{document_id}", response_model=DocumentSummaryResponse)
def update_document_metadata(
    document_id: str,
    payload: DocumentUpdateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> DocumentSummaryResponse:
    """Update document title, category, department, or access classification."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    if payload.category is not None:
        if payload.category not in DOCUMENT_CATEGORIES:
            raise HTTPException(status_code=400, detail="Invalid category.")
        doc.category = payload.category
    if payload.access_classification is not None:
        if payload.access_classification not in ACCESS_CLASSIFICATIONS:
            raise HTTPException(status_code=400, detail="Invalid access classification.")
        doc.access_classification = payload.access_classification
    if payload.title is not None:
        doc.title = payload.title.strip()
    if payload.department is not None:
        doc.department = payload.department.strip()
    if payload.collection_id is not None:
        doc.collection_id = payload.collection_id

    db.commit()
    db.refresh(doc)
    return _serialize_doc_summary(doc)


@router.post("/{document_id}/reprocess", response_model=DocumentSummaryResponse)
def trigger_reprocess(
    document_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> DocumentSummaryResponse:
    """Re-extract, re-chunk, and re-embed a document, replacing previous chunks."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    updated = reprocess_document(db, doc)
    return _serialize_doc_summary(updated)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> None:
    """Delete a document, its indexed chunks, and its stored source file."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    file_path = Path(doc.storage_path)
    db.delete(doc)
    db.commit()
    if file_path.exists():
        try:
            file_path.unlink()
        except OSError:
            pass

