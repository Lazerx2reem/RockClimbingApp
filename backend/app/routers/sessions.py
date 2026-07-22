from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import TrainingSession, User
from ..schemas import SessionCreate, SessionOut

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _get_owned_session(session_id: int, user: User, db: Session) -> TrainingSession:
    session = db.get(TrainingSession, session_id)
    if session is None or session.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )
    return session


@router.get("", response_model=list[SessionOut])
def list_sessions(
    session_type: str | None = Query(
        default=None, pattern="^(gym|board|outdoor|hangboard|other)$"
    ),
    date_from: date | None = None,
    date_to: date | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TrainingSession]:
    query = select(TrainingSession).where(TrainingSession.user_id == user.id)
    if session_type is not None:
        query = query.where(TrainingSession.session_type == session_type)
    if date_from is not None:
        query = query.where(TrainingSession.session_date >= date_from)
    if date_to is not None:
        query = query.where(TrainingSession.session_date <= date_to)
    query = query.order_by(TrainingSession.session_date.desc(), TrainingSession.id.desc())
    return list(db.scalars(query))


@router.post("", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
def create_session(
    payload: SessionCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TrainingSession:
    data = payload.model_dump()
    if data.get("workout_details") is not None:
        data["workout_details"] = [item for item in data["workout_details"]]
    session = TrainingSession(user_id=user.id, **data)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    session = _get_owned_session(session_id, user, db)
    db.delete(session)
    db.commit()
