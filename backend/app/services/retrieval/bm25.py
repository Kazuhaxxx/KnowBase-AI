import re
from typing import Optional

from rank_bm25 import BM25Plus
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk
from app.services.retrieval.types import RetrievedChunk

_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how",
    "i", "in", "is", "it", "my", "of", "on", "or", "that", "the", "this",
    "to", "was", "what", "when", "where", "which", "who", "why", "with",
}


def tokenize_for_bm25(text: str) -> list[str]:
    """
    Tokenize text while preserving IT error codes, versions, and hyphenated identifiers
    such as '0x80070005', 'err_connection_reset', 'vpn-403', or 'windows-11'.
    """
    raw_tokens = re.findall(r"[a-z0-9][a-z0-9_.-]*[a-z0-9]|[a-z0-9]+", text.lower())
    return [tok for tok in raw_tokens if tok not in _STOPWORDS and len(tok) > 1]


def bm25_retrieve(
    db: Session,
    query: str,
    allowed_classifications: list[str],
    top_k: int = 12,
    category_filter: Optional[str] = None,
    collection_id: Optional[str] = None,
) -> list[RetrievedChunk]:
    """Perform RBAC-filtered BM25 keyword retrieval over indexed document chunks."""
    if not allowed_classifications:
        return []

    query_tokens = tokenize_for_bm25(query)
    if not query_tokens:
        return []

    stmt = (
        db.query(DocumentChunk, Document)
        .join(Document, DocumentChunk.document_id == Document.id)
        .filter(
            Document.processing_status == "indexed",
            Document.access_classification.in_(allowed_classifications),
        )
    )
    if category_filter:
        stmt = stmt.filter(Document.category == category_filter)
    if collection_id:
        stmt = stmt.filter(Document.collection_id == collection_id)

    rows = stmt.all()
    if not rows:
        return []

    corpus_tokens = [
        tokenize_for_bm25(f"{doc.title} {chunk.section_heading or ''} {chunk.cleaned_content}")
        for chunk, doc in rows
    ]
    # Ensure non-empty documents in corpus
    non_empty_indices = [i for i, toks in enumerate(corpus_tokens) if toks]
    if not non_empty_indices:
        return []

    filtered_rows = [rows[i] for i in non_empty_indices]
    filtered_corpus = [corpus_tokens[i] for i in non_empty_indices]

    bm25 = BM25Plus(filtered_corpus)
    scores = bm25.get_scores(query_tokens)

    # BM25Plus adds delta=1.0 only for matched query terms; compute matched-term overlap to avoid 0-match noise
    query_token_set = set(query_tokens)
    max_score = float(max(scores)) if len(scores) > 0 else 0.0
    ranked_indices = sorted(
        range(len(scores)), key=lambda idx: float(scores[idx]), reverse=True
    )

    results: list[RetrievedChunk] = []
    for idx in ranked_indices[:top_k]:
        matched_terms = query_token_set.intersection(filtered_corpus[idx])
        if not matched_terms:
            continue
        raw_score = float(scores[idx])
        if raw_score <= 0.0:
            continue
        # Combine query-term coverage with relative BM25 rank so 1-word coincidences stay low
        term_ratio = len(matched_terms) / max(1, len(query_token_set))
        rel_score = raw_score / max_score if max_score > 0 else 0.0
        norm_score = min(1.0, rel_score * (0.35 + 0.65 * term_ratio))
        chunk, doc = filtered_rows[idx]
        results.append(
            RetrievedChunk(
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
                bm25_score=round(norm_score, 6),
                final_score=round(norm_score, 6),
                retrieval_sources=["bm25"],
                metadata=dict(chunk.metadata_json or {}),
            )
        )
    return results
