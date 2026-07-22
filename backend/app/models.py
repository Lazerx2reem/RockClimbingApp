from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(100))
    # Profile
    climbing_style: Mapped[str | None] = mapped_column(String(50))  # boulder / sport / trad / all
    home_gym: Mapped[str | None] = mapped_column(String(120))
    grade_range_boulder: Mapped[str | None] = mapped_column(String(20))  # e.g. "V3-V5"
    grade_range_route: Mapped[str | None] = mapped_column(String(20))  # e.g. "5.10c-5.11b"
    goals: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    climbs: Mapped[list["Climb"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    sessions: Mapped[list["TrainingSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Climb(Base):
    """A logged climb/boulder: one row per problem or route the user worked."""

    __tablename__ = "climbs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    grade: Mapped[str] = mapped_column(String(10))  # "V4" or "5.11a"
    grade_system: Mapped[str] = mapped_column(String(10), default="v_scale")  # v_scale / yds
    climb_type: Mapped[str] = mapped_column(String(10), default="boulder")  # boulder / sport / trad
    wall_angle: Mapped[str | None] = mapped_column(String(10))  # slab / vertical / overhang / roof
    location: Mapped[str | None] = mapped_column(String(120))
    send_type: Mapped[str] = mapped_column(String(10), default="project")  # flash / onsight / redpoint / repeat / project
    attempt_count: Mapped[int] = mapped_column(Integer, default=1)
    notes: Mapped[str | None] = mapped_column(Text)
    climbed_on: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped[User] = relationship(back_populates="climbs")
    attempts: Mapped[list["Attempt"]] = relationship(
        back_populates="climb", cascade="all, delete-orphan"
    )


class Attempt(Base):
    """An individual attempt on a climb. Will link to uploaded videos in phase 2."""

    __tablename__ = "attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    climb_id: Mapped[int] = mapped_column(
        ForeignKey("climbs.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    attempt_date: Mapped[date] = mapped_column(Date)
    outcome: Mapped[str] = mapped_column(String(10))  # send / fall / progress
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    climb: Mapped[Climb] = relationship(back_populates="attempts")


class TrainingSession(Base):
    """A training session: gym/board/outdoor day with duration, RPE, and workout details."""

    __tablename__ = "training_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    session_date: Mapped[date] = mapped_column(Date)
    session_type: Mapped[str] = mapped_column(String(20))  # gym / board / outdoor / hangboard / other
    duration_minutes: Mapped[int] = mapped_column(Integer)
    rpe: Mapped[int | None] = mapped_column(Integer)  # 1-10 rate of perceived exertion
    notes: Mapped[str | None] = mapped_column(Text)
    # Structured workout data, e.g. [{"exercise": "hangboard", "detail": "20mm 7/3 repeaters", "sets": 6}]
    workout_details: Mapped[list | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped[User] = relationship(back_populates="sessions")
