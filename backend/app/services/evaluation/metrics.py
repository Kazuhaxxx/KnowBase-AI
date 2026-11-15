from dataclasses import dataclass
import re

from app.services.retrieval.bm25 import tokenize_for_bm25
from app.services.retrieval.types import RetrievedChunk


@dataclass
class RetrievalQuestionResult:
    question_id: str
    category: str
    question: str
    expected_document: str
    retrieved_documents: list[str]
    recall_at_k: float
    precision_at_k: float
    reciprocal_rank: float
    context_relevance: float
    latency_ms: float


def compute_retrieval_metrics(
    expected_document: str,
    expected_keywords: list[str],
    retrieved_chunks: list[RetrievedChunk],
    k: int = 5,
    evidence_sufficient: bool = True,
) -> tuple[float, float, float, float]:
    """
    Compute deterministic retrieval evaluation metrics for a single question:
    - Recall@K
    - Precision@K
    - Reciprocal Rank (for MRR)
    - Context Relevance (token coverage of expected answer keywords in retrieved chunks)
    """
    top_chunks = retrieved_chunks[:k]

    # Out-of-scope / insufficient evidence test case
    if expected_document == "NONE":
        correctly_abstained = 1.0 if not evidence_sufficient else 0.0
        return correctly_abstained, correctly_abstained, correctly_abstained, correctly_abstained

    if not top_chunks:
        return 0.0, 0.0, 0.0, 0.0

    expected_norm = expected_document.strip().lower()
    matching_positions = [
        idx
        for idx, chunk in enumerate(top_chunks, start=1)
        if chunk.original_filename.strip().lower() == expected_norm
        or chunk.document_title.strip().lower() == expected_norm
    ]

    recall = 1.0 if matching_positions else 0.0
    precision = len(matching_positions) / len(top_chunks)
    reciprocal_rank = (1.0 / matching_positions[0]) if matching_positions else 0.0

    # Context relevance: fraction of expected answer concepts present in top-K retrieved text
    combined_context = " ".join(c.cleaned_content.lower() for c in top_chunks)
    context_tokens = set(tokenize_for_bm25(combined_context))

    if expected_keywords:
        hits = 0
        for kw in expected_keywords:
            kw_norm = kw.strip().lower()
            if kw_norm in combined_context or all(
                t in context_tokens for t in re.findall(r"[a-z0-9_.-]+", kw_norm) if len(t) > 1
            ):
                hits += 1
        context_relevance = hits / len(expected_keywords)
    else:
        context_relevance = recall

    return (
        round(recall, 4),
        round(precision, 4),
        round(reciprocal_rank, 4),
        round(context_relevance, 4),
    )

