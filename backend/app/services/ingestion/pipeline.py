from datetime import datetime, timezone
import hashlib
import logging
from pathlib import Path
from typing import Optional
import uuid

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.config import ACCESS_CLASSIFICATIONS, DOCUMENT_CATEGORIES, get_settings
from app.core.security import sanitize_filename
from app.models.document import Document, DocumentChunk
from app.services.embeddings.provider import EmbeddingService, get_embedding_service
from app.services.ingestion.chunker import chunk_segments
from app.services.ingestion.extractors import (
    DocumentExtractionError,
    extract_document,
    validate_upload_bytes,
)

logger = logging.getLogger("helpdesk_ai.ingestion")

MIME_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
    ".md": "text/markdown",
}


class IngestionOutcome:
    def __init__(
        self,
        document: Document,
        duplicate_detected: bool = False,
        replaced_previous_version: bool = False,
        message: str = "Document processed and indexed.",
    ) -> None:
        self.document = document
        self.duplicate_detected = duplicate_detected
        self.replaced_previous_version = replaced_previous_version
        self.message = message


def compute_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def ingest_uploaded_document(
    db: Session,
    filename: str,
    content: bytes,
    title: Optional[str],
    category: str,
    department: str,
    access_classification: str,
    uploaded_by_user_id: Optional[str],
    embedding_service: Optional[EmbeddingService] = None,
    collection_id: Optional[str] = None,
) -> IngestionOutcome:
    """
    Validate, deduplicate, store, extract, chunk, embed, and persist an uploaded document.
    Replaces prior chunks if a document with the same filename & title is updated.
    """
    settings = get_settings()

    if category not in DOCUMENT_CATEGORIES:
        raise DocumentExtractionError(
            f"Invalid category '{category}'. Allowed: {DOCUMENT_CATEGORIES}"
        )
    if access_classification not in ACCESS_CLASSIFICATIONS:
        raise DocumentExtractionError(
            f"Invalid access classification '{access_classification}'. Allowed: {ACCESS_CLASSIFICATIONS}"
        )

    ext = validate_upload_bytes(
        filename=filename,
        content=content,
        allowed_extensions=settings.allowed_extension_set,
        max_size_bytes=settings.max_upload_size_bytes,
    )

    file_hash = compute_sha256(content)
    existing_same_hash = db.query(Document).filter(Document.file_hash == file_hash).first()
    if existing_same_hash is not None:
        return IngestionOutcome(
            document=existing_same_hash,
            duplicate_detected=True,
            replaced_previous_version=False,
            message=f"Duplicate file detected (matches existing document '{existing_same_hash.title}').",
        )

    safe_name = sanitize_filename(filename)
    doc_title = (title or Path(safe_name).stem.replace("_", " ").replace("-", " ").title()).strip()

    # Check if an earlier version with the same original filename exists -> replace its chunks cleanly
    existing_by_name = (
        db.query(Document).filter(Document.original_filename == safe_name).first()
    )
    replaced = False

    upload_root = Path(settings.upload_dir)
    upload_root.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}_{safe_name}"
    storage_path = upload_root / stored_name
    storage_path.write_bytes(content)

    if existing_by_name is not None:
        doc = existing_by_name
        # Remove old file if present
        old_path = Path(doc.storage_path)
        if old_path.exists() and old_path != storage_path:
            try:
                old_path.unlink()
            except OSError:
                pass
        doc.title = doc_title
        doc.storage_path = str(storage_path)
        doc.mime_type = MIME_TYPES.get(ext, "application/octet-stream")
        doc.file_size_bytes = len(content)
        doc.file_hash = file_hash
        doc.category = category
        doc.department = department
        doc.access_classification = access_classification
        if collection_id is not None:
            doc.collection_id = collection_id
        doc.version = doc.version + 1
        doc.processing_status = "processing"
        doc.error_message = None
        doc.uploaded_by = uploaded_by_user_id
        db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == doc.id))
        db.flush()
        replaced = True
    else:
        doc = Document(
            title=doc_title,
            original_filename=safe_name,
            storage_path=str(storage_path),
            mime_type=MIME_TYPES.get(ext, "application/octet-stream"),
            file_size_bytes=len(content),
            file_hash=file_hash,
            category=category,
            department=department,
            access_classification=access_classification,
            collection_id=collection_id,
            version=1,
            processing_status="processing",
            uploaded_by=uploaded_by_user_id,
        )
        db.add(doc)
        db.flush()

    _process_document_chunks(db, doc, ext, embedding_service=embedding_service)
    db.commit()
    db.refresh(doc)

    return IngestionOutcome(
        document=doc,
        duplicate_detected=False,
        replaced_previous_version=replaced,
        message=(
            f"Updated document to v{doc.version} and replaced indexed chunks."
            if replaced
            else "Document uploaded, chunked, embedded, and indexed successfully."
        ),
    )


def reprocess_document(
    db: Session,
    doc: Document,
    embedding_service: Optional[EmbeddingService] = None,
) -> Document:
    """Re-extract, re-chunk, and re-embed an existing document, replacing prior chunks."""
    file_path = Path(doc.storage_path)
    if not file_path.exists():
        doc.processing_status = "failed"
        doc.error_message = "Stored source file no longer exists on disk."
        db.commit()
        db.refresh(doc)
        return doc

    ext = Path(doc.original_filename).suffix.lower()
    doc.processing_status = "processing"
    doc.error_message = None
    db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == doc.id))
    db.flush()

    _process_document_chunks(db, doc, ext, embedding_service=embedding_service)
    db.commit()
    db.refresh(doc)
    return doc


def _process_document_chunks(
    db: Session,
    doc: Document,
    extension: str,
    embedding_service: Optional[EmbeddingService] = None,
) -> None:
    settings = get_settings()
    embedder = embedding_service or get_embedding_service()

    try:
        extraction = extract_document(Path(doc.storage_path), extension)
        base_meta = {
            "document_id": doc.id,
            "document_title": doc.title,
            "original_filename": doc.original_filename,
            "category": doc.category,
            "department": doc.department,
            "access_classification": doc.access_classification,
            "version": doc.version,
        }
        chunks = chunk_segments(
            segments=extraction.segments,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            base_metadata=base_meta,
        )
        if not chunks:
            raise DocumentExtractionError("Document produced zero indexable chunks.")

        vectors = embedder.encode_documents([c.cleaned_content for c in chunks])
        for chunk_payload, vec in zip(chunks, vectors):
            db.add(
                DocumentChunk(
                    document_id=doc.id,
                    chunk_index=chunk_payload.chunk_index,
                    content=chunk_payload.content,
                    cleaned_content=chunk_payload.cleaned_content,
                    page_number=chunk_payload.page_number,
                    section_heading=chunk_payload.section_heading,
                    token_count=chunk_payload.token_count,
                    char_count=chunk_payload.char_count,
                    metadata_json=chunk_payload.metadata_json,
                    embedding_model=embedder.model_name,
                    embedding_dim=embedder.dimension,
                    embedding=vec,
                )
            )

        doc.page_count = extraction.page_count
        doc.extracted_preview = extraction.full_text_preview
        doc.chunk_count = len(chunks)
        doc.processing_status = "indexed"
        doc.error_message = None
        doc.last_processed_at = datetime.now(timezone.utc)
    except Exception as exc:
        logger.exception("Document processing failed for doc_id=%s", doc.id)
        doc.processing_status = "failed"
        doc.error_message = str(exc)[:1000]
        doc.chunk_count = 0
        doc.last_processed_at = datetime.now(timezone.utc)

