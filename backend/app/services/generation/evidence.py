from dataclasses import dataclass
import re

from app.core.config import get_settings
from app.services.retrieval.bm25 import tokenize_for_bm25
from app.services.retrieval.types import RetrievedChunk


@dataclass
class EvidenceAssessment:
    sufficient: bool
    confidence_score: float
    top_score: float
    term_coverage: float
    selected_chunks: list[RetrievedChunk]
    reason: str


def filter_coherent_chunks(chunks: list[RetrievedChunk], max_chunks: int = 5) -> list[RetrievedChunk]:
    """
    Prevent unrelated low-scoring documents from polluting the prompt context.
    Keeps chunks within a reasonable score margin of the top retrieved chunk.
    """
    if not chunks:
        return []
    top_score = chunks[0].final_score
    # Allow chunks that achieve at least 45% of the top chunk's final score (or high absolute score)
    threshold = max(0.12, top_score * 0.45)
    filtered = [c for c in chunks if c.final_score >= threshold]
    if not filtered:
        filtered = [chunks[0]]
    return filtered[:max_chunks]


def assess_evidence_sufficiency(
    query: str,
    chunks: list[RetrievedChunk],
) -> EvidenceAssessment:
    """
    Non-LLM-self-report evidence sufficiency check combining:
    1. Top retrieval/rerank relevance score
    2. Query-to-evidence lexical/identifier coverage
    3. Coherent context selection
    """
    settings = get_settings()
    if not chunks:
        return EvidenceAssessment(
            sufficient=False,
            confidence_score=0.0,
            top_score=0.0,
            term_coverage=0.0,
            selected_chunks=[],
            reason="No accessible chunks matched the query.",
        )

    coherent = filter_coherent_chunks(chunks, max_chunks=settings.retrieval_top_n_final)
    top_chunk = coherent[0]
    top_score = float(top_chunk.final_score)

    query_tokens = set(tokenize_for_bm25(query))
    combined_text = " ".join(f"{c.document_title} {c.cleaned_content}" for c in coherent)
    evidence_tokens = set(tokenize_for_bm25(combined_text))

    if query_tokens:
        overlap = query_tokens.intersection(evidence_tokens)
        term_coverage = len(overlap) / len(query_tokens)
    else:
        term_coverage = 0.0

    # Weighted objective confidence score (0.0 to 1.0)
    confidence = round(min(1.0, 0.65 * top_score + 0.35 * term_coverage), 4)

    # Check if either semantic/rerank score + coverage pass thresholds,
    # and prevent weak 1-word BM25 collisions or low CrossEncoder logits from passing.
    if top_chunk.rerank_score is not None:
        score_ok = top_chunk.rerank_score >= 0.15 or (
            top_score >= settings.evidence_min_score and top_chunk.semantic_score >= 0.25
        )
    else:
        semantic_or_direct = (
            top_chunk.semantic_score >= 0.20 if "semantic" in top_chunk.retrieval_sources else True
        )
        score_ok = top_score >= settings.evidence_min_score and semantic_or_direct

    coverage_ok = term_coverage >= max(settings.evidence_min_term_coverage, 0.25)

    sufficient = bool(score_ok and coverage_ok)
    reason = (
        "Sufficient supporting documentation retrieved."
        if sufficient
        else f"Insufficient evidence (top_score={top_score:.3f}, term_coverage={term_coverage:.3f})."
    )
    return EvidenceAssessment(
        sufficient=sufficient,
        confidence_score=confidence,
        top_score=round(top_score, 4),
        term_coverage=round(term_coverage, 4),
        selected_chunks=coherent if sufficient else [],
        reason=reason,
    )


def validate_and_select_citations(
    response_text: str,
    context_chunks: list[RetrievedChunk],
) -> tuple[str, list[RetrievedChunk]]:
    """
    Verify that every [Source N] marker in the generated response maps to an actual chunk
    sent in the context. Strips any invalid/fabricated source markers and returns the
    ordered list of cited chunks (or top context chunks if model omitted inline markers).
    """
    if not context_chunks:
        return response_text, []

    valid_indices = set(range(1, len(context_chunks) + 1))
    referenced_order: list[int] = []

    def _replace_marker(match: re.Match[str]) -> str:
        idx = int(match.group(1))
        if idx in valid_indices:
            if idx not in referenced_order:
                referenced_order.append(idx)
            return f"[Source {idx}]"
        # Strip fabricated citation index
        return ""

    cleaned_response = re.sub(
        r"\[(?:Source\s*)?(\d+)\]",
        _replace_marker,
        response_text,
        flags=re.IGNORECASE,
    )
    # Collapse double spaces caused by stripped invalid citations
    cleaned_response = re.sub(r" {2,}", " ", cleaned_response).strip()

    if referenced_order:
        cited = [context_chunks[i - 1] for i in referenced_order]
    else:
        # Attach top used context chunks (max 3) when model wrote grounded prose without tags
        cited = context_chunks[: min(3, len(context_chunks))]

    return cleaned_response, cited

