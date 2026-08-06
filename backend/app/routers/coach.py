import json
from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..coach.service import coach_available, stream_reply
from ..config import settings
from ..database import SessionLocal, get_db
from ..models import CoachMessage, Conversation, User
from ..schemas import (
    CoachMessageCreate,
    CoachMessageOut,
    ConversationCreate,
    ConversationDetailOut,
    ConversationOut,
)

router = APIRouter(prefix="/coach", tags=["coach"])

# Longest auto-derived conversation title before it gets an ellipsis.
TITLE_LENGTH = 60


def _get_owned_conversation(
    conversation_id: int, user: User, db: Session
) -> Conversation:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None or conversation.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )
    return conversation


def _derive_title(text: str) -> str:
    single_line = " ".join(text.split())
    if len(single_line) <= TITLE_LENGTH:
        return single_line
    return single_line[: TITLE_LENGTH - 1].rstrip() + "…"


def _require_coach() -> None:
    if not coach_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The AI coach is not configured. Set ANTHROPIC_API_KEY in backend/.env.",
        )


@router.get("/status")
def coach_status(user: User = Depends(get_current_user)) -> dict:
    """Lets the UI explain a missing key instead of failing on first message."""
    return {"available": coach_available(), "model": settings.coach_model}


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Conversation]:
    query = (
        select(Conversation)
        .where(Conversation.user_id == user.id)
        .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
    )
    return list(db.scalars(query))


@router.post(
    "/conversations",
    response_model=ConversationDetailOut,
    status_code=status.HTTP_201_CREATED,
)
def create_conversation(
    payload: ConversationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Conversation:
    conversation = Conversation(
        user_id=user.id, title=payload.title or "New conversation"
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailOut)
def get_conversation(
    conversation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Conversation:
    return _get_owned_conversation(conversation_id, user, db)


@router.delete(
    "/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_conversation(
    conversation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    conversation = _get_owned_conversation(conversation_id, user, db)
    db.delete(conversation)
    db.commit()


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


def _reply_stream(conversation_id: int, user_id: int) -> Iterator[str]:
    """Run one coach turn and emit it as server-sent events.

    Owns its own session: the request-scoped one from `get_db` is torn down
    around the response, which for a streaming response is the wrong lifetime.
    Same reasoning as the phase 2 background analyzer.
    """
    db = SessionLocal()
    try:
        user = db.get(User, user_id)
        conversation = db.get(Conversation, conversation_id)
        if user is None or conversation is None:
            yield _sse({"type": "error", "message": "Conversation not found."})
            return

        # Oldest-first transcript, trimmed to the most recent N turns.
        history = [
            {"role": m.role, "content": m.content}
            for m in conversation.messages[-settings.coach_history_limit :]
        ]

        for event in stream_reply(user, db, history):
            if event["type"] != "complete":
                yield _sse(event)
                continue

            if not event["text"]:
                yield _sse(
                    {"type": "error", "message": "The coach returned an empty reply."}
                )
                return

            reply = CoachMessage(
                conversation_id=conversation.id,
                user_id=user.id,
                role="assistant",
                content=event["text"],
                tool_calls=event["tool_calls"] or None,
            )
            db.add(reply)
            db.commit()
            db.refresh(reply)
            yield _sse({"type": "done", "message_id": reply.id})
    finally:
        db.close()


@router.post("/conversations/{conversation_id}/messages")
def send_message(
    conversation_id: int,
    payload: CoachMessageCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Persist the user's message, then stream the coach's reply as SSE.

    Streamed rather than returned whole because a turn can involve several tool
    round-trips before the first word of the answer exists.
    """
    _require_coach()
    conversation = _get_owned_conversation(conversation_id, user, db)

    # Checked before the insert — appending would autoflush and make the
    # relationship non-empty on every turn.
    is_first = not conversation.messages
    db.add(
        CoachMessage(
            conversation_id=conversation.id,
            user_id=user.id,
            role="user",
            content=payload.content,
        )
    )
    if is_first:
        conversation.title = _derive_title(payload.content)
    db.commit()

    return StreamingResponse(
        _reply_stream(conversation.id, user.id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # don't let a proxy buffer the stream
        },
    )


@router.get(
    "/conversations/{conversation_id}/messages", response_model=list[CoachMessageOut]
)
def list_messages(
    conversation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CoachMessage]:
    return _get_owned_conversation(conversation_id, user, db).messages
