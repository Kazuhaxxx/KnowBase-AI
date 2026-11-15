from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.chat import Conversation, Feedback, Message
from app.models.user import User
from app.schemas.chat import FeedbackRequest, FeedbackResponse

router = APIRouter(prefix="/feedback", tags=["Feedback"])


@router.post("", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
def submit_feedback(
    payload: FeedbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FeedbackResponse:
    """Submit helpful / not_helpful feedback on an assistant message owned by the user."""
    msg = (
        db.query(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(
            Message.id == payload.message_id,
            Conversation.user_id == current_user.id,
            Message.role == "assistant",
        )
        .first()
    )
    if msg is None:
        raise HTTPException(
            status_code=404,
            detail="Assistant message not found or access denied.",
        )

    existing = (
        db.query(Feedback)
        .filter(Feedback.message_id == msg.id, Feedback.user_id == current_user.id)
        .first()
    )
    if existing is not None:
        existing.rating = payload.rating
        existing.comment = payload.comment
        db.commit()
        db.refresh(existing)
        return FeedbackResponse(
            id=existing.id,
            message_id=existing.message_id,
            rating=existing.rating,
            comment=existing.comment,
            created_at=existing.created_at,
        )

    fb = Feedback(
        message_id=msg.id,
        user_id=current_user.id,
        rating=payload.rating,
        comment=payload.comment,
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return FeedbackResponse(
        id=fb.id,
        message_id=fb.message_id,
        rating=fb.rating,
        comment=fb.comment,
        created_at=fb.created_at,
    )

