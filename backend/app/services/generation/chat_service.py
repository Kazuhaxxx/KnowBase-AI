from datetime import datetime, timezone
import logging
import time
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import get_allowed_classifications
from app.models.chat import Conversation, Message, MessageCitation
from app.models.evaluation import QueryTelemetry
from app.models.user import User
from app.services.generation.evidence import (
    assess_evidence_sufficiency,
    validate_and_select_citations,
)
from app.services.generation.prompts import (
    INSUFFICIENT_EVIDENCE_FALLBACK,
    SYSTEM_PROMPT,
    build_user_prompt,
)
from app.services.generation.providers import LLMProvider, LLMUnavailableError, get_llm_provider
from app.services.reranking.cross_encoder import get_reranker
from app.services.retrieval.hybrid import hybrid_retrieve
from app.services.retrieval.query_rewriter import rewrite_query
from app.services.retrieval.types import RetrievedChunk

logger = logging.getLogger("helpdesk_ai.chat")


async def process_chat_turn(
    db: Session,
    user: User,
    question: str,
    conversation_id: Optional[str] = None,
    category_filter: Optional[str] = None,
    collection_id: Optional[str] = None,
    retrieval_mode: str = "hybrid_rerank",
    llm_provider: Optional[LLMProvider] = None,
) -> tuple[Conversation, Message, Message]:
    """
    Execute the complete, RBAC-enforced RAG pipeline for a user question:
    1. Load or create user-owned conversation.
    2. Rewrite query safely using recent turn context.
    3. Retrieve RBAC-filtered candidates (semantic / hybrid).
    4. Rerank with cross-encoder (if mode == 'hybrid_rerank').
    5. Assess objective evidence sufficiency.
    6. Generate grounded answer via active LLM provider (or fallback if insufficient evidence).
    7. Validate citations, persist messages & non-sensitive telemetry.
    """
    settings = get_settings()
    total_start = time.perf_counter()

    # 1. Conversation ownership check
    if conversation_id:
        conversation = (
            db.query(Conversation)
            .filter(Conversation.id == conversation_id, Conversation.user_id == user.id)
            .first()
        )
        if conversation is None:
            raise PermissionError("Conversation not found or access denied.")
    else:
        title = question.strip()[:72] + ("..." if len(question.strip()) > 72 else "")
        conversation = Conversation(user_id=user.id, title=title or "Knowledge Query")
        db.add(conversation)
        db.flush()

    recent_turns = [
        m.content
        for m in db.query(Message)
        .filter(Message.conversation_id == conversation.id, Message.role == "user")
        .order_by(Message.created_at.desc())
        .limit(3)
        .all()
    ]
    recent_turns.reverse()

    user_msg = Message(
        conversation_id=conversation.id,
        role="user",
        content=question.strip(),
    )
    db.add(user_msg)
    db.flush()

    # 2. Query rewriting
    rewritten = rewrite_query(
        query=question,
        recent_user_turns=recent_turns,
        enabled=settings.enable_query_rewriting,
    )

    # 3. Server-derived RBAC classifications (cannot be overridden by client)
    allowed_classifications = get_allowed_classifications(user.role.name)

    ret_start = time.perf_counter()
    candidates = hybrid_retrieve(
        db=db,
        query=rewritten,
        allowed_classifications=allowed_classifications,
        mode=retrieval_mode,
        top_n=settings.retrieval_top_n_final,
        category_filter=category_filter,
        collection_id=collection_id,
    )

    # 4. Cross-encoder reranking
    if retrieval_mode == "hybrid_rerank" and candidates:
        reranker = get_reranker()
        ranked_chunks, _ = reranker.rerank(
            query=question,
            candidates=candidates,
            top_n=settings.retrieval_top_n_final,
        )
    else:
        ranked_chunks = candidates[: settings.retrieval_top_n_final]
    retrieval_latency_ms = round((time.perf_counter() - ret_start) * 1000, 2)

    # 5. Evidence sufficiency assessment
    assessment = assess_evidence_sufficiency(question, ranked_chunks)

    gen_start = time.perf_counter()
    provider = llm_provider or get_llm_provider()
    provider_used = provider.provider_name
    model_used = provider.model_name
    cited_chunks: list[RetrievedChunk] = []

    if not assessment.sufficient:
        answer_text = INSUFFICIENT_EVIDENCE_FALLBACK
        provider_used = "evidence_guard"
        model_used = "deterministic"
    else:
        user_prompt = build_user_prompt(question=question, chunks=assessment.selected_chunks)
        try:
            gen_result = await provider.generate(SYSTEM_PROMPT, user_prompt)
            answer_text, cited_chunks = validate_and_select_citations(
                gen_result.content,
                assessment.selected_chunks,
            )
            provider_used = gen_result.provider
            model_used = gen_result.model
        except LLMUnavailableError:
            # Propagate explicit service error rather than faking an LLM answer
            db.rollback()
            raise

    generation_latency_ms = round((time.perf_counter() - gen_start) * 1000, 2)
    total_latency_ms = round((time.perf_counter() - total_start) * 1000, 2)

    assistant_msg = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=answer_text,
        rewritten_query=rewritten if rewritten != question.strip() else None,
        confidence_score=assessment.confidence_score,
        evidence_sufficient=assessment.sufficient,
        provider_used=provider_used,
        model_used=model_used,
        retrieval_latency_ms=retrieval_latency_ms,
        generation_latency_ms=generation_latency_ms,
        total_latency_ms=total_latency_ms,
    )
    db.add(assistant_msg)
    db.flush()

    for idx, chunk in enumerate(cited_chunks, start=1):
        db.add(
            MessageCitation(
                message_id=assistant_msg.id,
                document_id=chunk.document_id,
                chunk_id=chunk.chunk_id,
                document_title=chunk.document_title,
                original_filename=chunk.original_filename,
                page_number=chunk.page_number,
                chunk_index=chunk.chunk_index,
                passage_excerpt=chunk.cleaned_content[:900],
                relevance_score=chunk.final_score,
                rank_order=idx,
            )
        )

    # Non-sensitive telemetry (no prompt text, no document text, no user ID)
    inferred_category = (
        cited_chunks[0].category
        if cited_chunks
        else (ranked_chunks[0].category if ranked_chunks else category_filter)
    )
    db.add(
        QueryTelemetry(
            category=inferred_category,
            retrieval_mode=retrieval_mode,
            evidence_sufficient=assessment.sufficient,
            top_score=assessment.top_score,
            retrieval_latency_ms=retrieval_latency_ms,
            generation_latency_ms=generation_latency_ms,
            total_latency_ms=total_latency_ms,
            retrieved_document_ids=list({c.document_id for c in cited_chunks}),
        )
    )

    conversation.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(conversation)
    db.refresh(user_msg)
    db.refresh(assistant_msg)
    return conversation, user_msg, assistant_msg

