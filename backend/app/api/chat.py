import json
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, limiter
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import get_allowed_classifications
from app.models.chat import Conversation, Message
from app.models.document import Document
from app.models.user import User
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    CitationResponse,
    ConversationDetailResponse,
    ConversationSummaryResponse,
    MessageResponse,
)
from app.services.generation.chat_service import process_chat_turn
from app.services.generation.providers import LLMUnavailableError

router = APIRouter(tags=["Chat & Conversations"])
settings = get_settings()


def _serialize_message(msg: Message) -> MessageResponse:
    return MessageResponse(
        id=msg.id,
        role=msg.role,
        content=msg.content,
        rewritten_query=msg.rewritten_query,
        confidence_score=msg.confidence_score,
        evidence_sufficient=msg.evidence_sufficient,
        provider_used=msg.provider_used,
        model_used=msg.model_used,
        retrieval_latency_ms=msg.retrieval_latency_ms,
        generation_latency_ms=msg.generation_latency_ms,
        total_latency_ms=msg.total_latency_ms,
        citations=[
            CitationResponse(
                id=c.id,
                document_id=c.document_id,
                chunk_id=c.chunk_id,
                document_title=c.document_title,
                original_filename=c.original_filename,
                page_number=c.page_number,
                chunk_index=c.chunk_index,
                passage_excerpt=c.passage_excerpt,
                relevance_score=c.relevance_score,
                rank_order=c.rank_order,
            )
            for c in msg.citations
        ],
        created_at=msg.created_at,
    )


@router.post("/chat", response_model=ChatResponse)
@limiter.limit(settings.rate_limit_chat)
async def chat(
    request: Request,
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    """Ask an IT support question and receive an evidence-grounded response with citations."""
    try:
        conv, user_msg, assistant_msg = await process_chat_turn(
            db=db,
            user=current_user,
            question=payload.question,
            conversation_id=payload.conversation_id,
            category_filter=payload.category_filter,
            collection_id=payload.collection_id,
            retrieval_mode=payload.retrieval_mode or "hybrid_rerank",
        )
    except PermissionError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LLMUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return ChatResponse(
        conversation_id=conv.id,
        conversation_title=conv.title,
        user_message=_serialize_message(user_msg),
        assistant_message=_serialize_message(assistant_msg),
    )


@router.post("/chat/stream")
@limiter.limit(settings.rate_limit_chat)
async def chat_stream(
    request: Request,
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Stream the grounded response and final citation payload as Server-Sent Events (SSE)."""

    async def event_generator() -> AsyncGenerator[str, None]:
        # Send immediate initial SSE byte to keep tunnel connections open and prevent gateway timeouts
        yield f"data: {json.dumps({'type': 'ping'})}\n\n"
        try:
            conv, user_msg, assistant_msg = await process_chat_turn(
                db=db,
                user=current_user,
                question=payload.question,
                conversation_id=payload.conversation_id,
                category_filter=payload.category_filter,
                collection_id=payload.collection_id,
                retrieval_mode=payload.retrieval_mode or "hybrid_rerank",
            )
            # Stream text chunks smoothly over SSE, followed by complete structured metadata
            words = assistant_msg.content.split(" ")
            for i in range(0, len(words), 4):
                token_chunk = " ".join(words[i : i + 4]) + (" " if i + 4 < len(words) else "")
                yield f"data: {json.dumps({'type': 'token', 'content': token_chunk})}\n\n"

            done_payload = ChatResponse(
                conversation_id=conv.id,
                conversation_title=conv.title,
                user_message=_serialize_message(user_msg),
                assistant_message=_serialize_message(assistant_msg),
            ).model_dump(mode="json")
            yield f"data: {json.dumps({'type': 'done', 'payload': done_payload})}\n\n"
        except PermissionError as exc:
            yield f"data: {json.dumps({'type': 'error', 'detail': str(exc)})}\n\n"
        except LLMUnavailableError as exc:
            yield f"data: {json.dumps({'type': 'error', 'detail': str(exc)})}\n\n"
        except Exception as exc:
            logger.exception("Unexpected error in chat stream: %s", exc)
            yield f"data: {json.dumps({'type': 'error', 'detail': f'Generation error: {exc}'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/conversations", response_model=list[ConversationSummaryResponse])
def list_conversations(
    q: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ConversationSummaryResponse]:
    """List personal conversations belonging strictly to the authenticated user."""
    query = (
        db.query(Conversation)
        .options(joinedload(Conversation.messages))
        .filter(Conversation.user_id == current_user.id)
    )
    if q and q.strip():
        term = f"%{q.strip().lower()}%"
        query = query.filter(Conversation.title.ilike(term))

    convs = query.order_by(Conversation.updated_at.desc()).all()
    results: list[ConversationSummaryResponse] = []
    for c in convs:
        last_msg = c.messages[-1].content[:120] if c.messages else None
        results.append(
            ConversationSummaryResponse(
                id=c.id,
                title=c.title,
                created_at=c.created_at,
                updated_at=c.updated_at,
                message_count=len(c.messages),
                last_message_preview=last_msg,
            )
        )
    return results


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationDetailResponse:
    """Fetch a conversation and its messages/citations only if owned by the current user."""
    conv = (
        db.query(Conversation)
        .options(joinedload(Conversation.messages).joinedload(Message.citations))
        .filter(Conversation.id == conversation_id, Conversation.user_id == current_user.id)
        .first()
    )
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    return ConversationDetailResponse(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=[_serialize_message(m) for m in conv.messages],
    )


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a personal conversation owned by the current user."""
    conv = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == current_user.id)
        .first()
    )
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    db.delete(conv)
    db.commit()


@router.get("/dashboard/summary")
def employee_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Employee portal dashboard overview: personal usage, recent queries, and accessible docs."""
    allowed = get_allowed_classifications(current_user.role.name)

    accessible_docs = (
        db.query(Document)
        .filter(
            Document.processing_status == "indexed",
            Document.access_classification.in_(allowed),
        )
        .order_by(Document.last_processed_at.desc(), Document.created_at.desc())
        .limit(6)
        .all()
    )
    total_accessible = (
        db.query(func.count(Document.id))
        .filter(
            Document.processing_status == "indexed",
            Document.access_classification.in_(allowed),
        )
        .scalar()
        or 0
    )

    my_convs = (
        db.query(Conversation)
        .filter(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
        .limit(5)
        .all()
    )
    my_conv_count = (
        db.query(func.count(Conversation.id))
        .filter(Conversation.user_id == current_user.id)
        .scalar()
        or 0
    )
    my_question_count = (
        db.query(func.count(Message.id))
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(Conversation.user_id == current_user.id, Message.role == "user")
        .scalar()
        or 0
    )

    return {
        "user": {
            "full_name": current_user.full_name,
            "role": current_user.role.name,
            "department": current_user.department,
        },
        "usage": {
            "conversations": my_conv_count,
            "questions_asked": my_question_count,
            "accessible_articles": total_accessible,
        },
        "recent_conversations": [
            {
                "id": c.id,
                "title": c.title,
                "updated_at": c.updated_at,
            }
            for c in my_convs
        ],
        "recently_updated_articles": [
            {
                "id": d.id,
                "title": d.title,
                "category": d.category,
                "access_classification": d.access_classification,
                "last_processed_at": d.last_processed_at,
            }
            for d in accessible_docs
        ],
        "popular_topics": [
            {
                "topic": "VPN Connection",
                "prompt": "Why does my NovaPulse VPN fail with error VPN-403 or timeout?",
            },
            {
                "topic": "Outlook OST Sync",
                "prompt": "Outlook is stuck on Updating Inbox. How do I rebuild the OST cache safely?",
            },
            {
                "topic": "Password & MFA",
                "prompt": "How do I reset my corporate password and re-enroll Microsoft Authenticator MFA?",
            },
            {
                "topic": "Office Printers",
                "prompt": "How do I set up Follow-Me Print and clear a stuck print queue?",
            },
        ],
    }

