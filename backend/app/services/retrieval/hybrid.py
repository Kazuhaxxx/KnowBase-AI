from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services.embeddings.provider import EmbeddingService
from app.services.retrieval.bm25 import bm25_retrieve
from app.services.retrieval.semantic import semantic_retrieve
from app.services.retrieval.types import RetrievedChunk


def reciprocal_rank_fusion(
    semantic_hits: list[RetrievedChunk],
    bm25_hits: list[RetrievedChunk],
    rrf_k: int = 60,
    semantic_weight: float = 0.6,
    bm25_weight: float = 0.4,
    top_n: int = 10,
) -> list[RetrievedChunk]:
    """Combine semantic and BM25 ranked lists using weighted Reciprocal Rank Fusion (RRF)."""
    merged: dict[str, RetrievedChunk] = {}

    # Theoretical maximum RRF score when ranked #1 in both lists (used for 0..1 scaling)
    max_possible = (semantic_weight + bm25_weight) / (rrf_k + 1)

    for rank, item in enumerate(semantic_hits, start=1):
        rrf_contrib = semantic_weight / (rrf_k + rank)
        existing = merged.get(item.chunk_id)
        if existing is None:
            item.rrf_score = rrf_contrib
            item.final_score = rrf_contrib / max_possible if max_possible > 0 else rrf_contrib
            merged[item.chunk_id] = item
        else:
            existing.semantic_score = item.semantic_score
            existing.rrf_score += rrf_contrib
            if "semantic" not in existing.retrieval_sources:
                existing.retrieval_sources.append("semantic")
            existing.final_score = (
                existing.rrf_score / max_possible if max_possible > 0 else existing.rrf_score
            )

    for rank, item in enumerate(bm25_hits, start=1):
        rrf_contrib = bm25_weight / (rrf_k + rank)
        existing = merged.get(item.chunk_id)
        if existing is None:
            item.rrf_score = rrf_contrib
            item.final_score = rrf_contrib / max_possible if max_possible > 0 else rrf_contrib
            merged[item.chunk_id] = item
        else:
            existing.bm25_score = item.bm25_score
            existing.rrf_score += rrf_contrib
            if "bm25" not in existing.retrieval_sources:
                existing.retrieval_sources.append("bm25")
            existing.final_score = (
                existing.rrf_score / max_possible if max_possible > 0 else existing.rrf_score
            )

    combined = list(merged.values())
    for item in combined:
        item.rrf_score = round(item.rrf_score, 6)
        # Blend normalized RRF rank score with raw semantic similarity for stable thresholding
        blended = 0.55 * item.final_score + 0.45 * max(item.semantic_score, item.bm25_score)
        item.final_score = round(min(1.0, blended), 6)

    combined.sort(key=lambda c: (c.rrf_score, c.final_score), reverse=True)
    return combined[:top_n]


def hybrid_retrieve(
    db: Session,
    query: str,
    allowed_classifications: list[str],
    mode: str = "hybrid",
    top_n: Optional[int] = None,
    category_filter: Optional[str] = None,
    collection_id: Optional[str] = None,
    embedding_service: Optional[EmbeddingService] = None,
) -> list[RetrievedChunk]:
    """
    Execute retrieval in 'semantic', 'hybrid', or 'hybrid_rerank' (candidate generation) mode.
    Strict RBAC classification filtering is enforced inside both semantic and BM25 engines.
    """
    settings = get_settings()
    final_limit = top_n or settings.retrieval_top_n_final

    if mode == "semantic":
        return semantic_retrieve(
            db=db,
            query=query,
            allowed_classifications=allowed_classifications,
            top_k=final_limit,
            category_filter=category_filter,
            collection_id=collection_id,
            embedding_service=embedding_service,
        )

    candidate_limit = max(final_limit * 3, settings.retrieval_top_k_semantic)
    sem_hits = semantic_retrieve(
        db=db,
        query=query,
        allowed_classifications=allowed_classifications,
        top_k=candidate_limit,
        category_filter=category_filter,
        collection_id=collection_id,
        embedding_service=embedding_service,
    )
    bm25_hits = bm25_retrieve(
        db=db,
        query=query,
        allowed_classifications=allowed_classifications,
        top_k=max(final_limit * 3, settings.retrieval_top_k_bm25),
        category_filter=category_filter,
        collection_id=collection_id,
    )

    return reciprocal_rank_fusion(
        semantic_hits=sem_hits,
        bm25_hits=bm25_hits,
        rrf_k=settings.rrf_k,
        semantic_weight=settings.semantic_weight,
        bm25_weight=settings.bm25_weight,
        top_n=candidate_limit if mode == "hybrid_rerank" else final_limit,
    )

