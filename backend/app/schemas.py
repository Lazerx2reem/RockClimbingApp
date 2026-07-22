from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# ---------- Auth / users ----------


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    display_name: str = Field(min_length=1, max_length=100)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    display_name: str
    climbing_style: str | None = None
    home_gym: str | None = None
    grade_range_boulder: str | None = None
    grade_range_route: str | None = None
    goals: str | None = None
    created_at: datetime


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    climbing_style: str | None = None
    home_gym: str | None = None
    grade_range_boulder: str | None = None
    grade_range_route: str | None = None
    goals: str | None = None


# ---------- Climbs ----------


class ClimbBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    grade: str = Field(min_length=1, max_length=10)
    grade_system: str = Field(default="v_scale", pattern="^(v_scale|yds)$")
    climb_type: str = Field(default="boulder", pattern="^(boulder|sport|trad)$")
    wall_angle: str | None = Field(default=None, pattern="^(slab|vertical|overhang|roof)$")
    location: str | None = Field(default=None, max_length=120)
    send_type: str = Field(
        default="project", pattern="^(flash|onsight|redpoint|repeat|project)$"
    )
    attempt_count: int = Field(default=1, ge=1)
    notes: str | None = None
    climbed_on: date


class ClimbCreate(ClimbBase):
    pass


class ClimbUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    grade: str | None = Field(default=None, min_length=1, max_length=10)
    grade_system: str | None = Field(default=None, pattern="^(v_scale|yds)$")
    climb_type: str | None = Field(default=None, pattern="^(boulder|sport|trad)$")
    wall_angle: str | None = Field(default=None, pattern="^(slab|vertical|overhang|roof)$")
    location: str | None = Field(default=None, max_length=120)
    send_type: str | None = Field(
        default=None, pattern="^(flash|onsight|redpoint|repeat|project)$"
    )
    attempt_count: int | None = Field(default=None, ge=1)
    notes: str | None = None
    climbed_on: date | None = None


class ClimbOut(ClimbBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


# ---------- Attempts ----------


class AttemptCreate(BaseModel):
    attempt_date: date
    outcome: str = Field(pattern="^(send|fall|progress)$")
    notes: str | None = None


class AttemptOut(AttemptCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    climb_id: int


# ---------- Training sessions ----------


class WorkoutItem(BaseModel):
    exercise: str = Field(min_length=1, max_length=40)  # hangboard / campus / core / other
    detail: str = Field(default="", max_length=200)  # e.g. "20mm 7/3 repeaters"
    sets: int = Field(default=1, ge=1)


class SessionBase(BaseModel):
    session_date: date
    session_type: str = Field(pattern="^(gym|board|outdoor|hangboard|other)$")
    duration_minutes: int = Field(ge=1)
    rpe: int | None = Field(default=None, ge=1, le=10)
    notes: str | None = None
    workout_details: list[WorkoutItem] | None = None


class SessionCreate(SessionBase):
    pass


class SessionOut(SessionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


# ---------- Stats ----------


class PyramidEntry(BaseModel):
    grade: str
    count: int


class ProgressPoint(BaseModel):
    month: str  # "2026-07"
    sends: int


class AngleEntry(BaseModel):
    wall_angle: str
    count: int


class StatsSummary(BaseModel):
    total_climbs: int
    total_sends: int
    total_sessions: int
    total_hours: float
    hardest_boulder: str | None
    hardest_route: str | None
