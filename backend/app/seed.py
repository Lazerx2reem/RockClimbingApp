"""Seed the database with a demo user and realistic mock data.

Usage (after `alembic upgrade head`):

    python -m app.seed

Idempotent: skips seeding if the demo user already exists.
"""
import random
from datetime import date, timedelta

from sqlalchemy import select

from .auth import hash_password
from .database import SessionLocal
from .models import Climb, TrainingSession, User

DEMO_EMAIL = "demo@ascent.app"
DEMO_PASSWORD = "demo1234"

BOULDER_NAMES = [
    "Cave Dweller", "Crimp Ladder", "The Prow", "Slopey Joe", "Dyno-mite",
    "Left Arete", "Pinch Point", "Moonwalk", "Toe Hook Traverse", "The Egg",
    "Compression Session", "Gaston Alley", "Heelraiser", "Pocket Change",
    "Mantle Piece", "Sit Start Sally", "The Bulge", "Undercling Thing",
    "Campus Crusher", "Friction Addiction", "The Scoop", "Deadpoint Dance",
]
ROUTE_NAMES = [
    "Skyline Ridge", "Golden Hour", "Jug Haul", "Endurance Test", "The Runout",
    "Chalk Dust Dreams", "Second Pitch", "Anchor Baby", "Crux Mutiny", "Rest Jug City",
]
GYM_LOCATIONS = ["Boulder Barn", "The Crag Gym", "Vertical Limit"]
OUTDOOR_LOCATIONS = ["Bishop - Buttermilks", "Joe's Valley", "Red Rocks", "Castle Rock"]
ANGLES = ["slab", "vertical", "overhang", "roof"]
ANGLE_WEIGHTS = [0.15, 0.4, 0.35, 0.1]

# Grade distribution shaped like a real pyramid around a V4-V5 climber
BOULDER_GRADES = ["V0", "V1", "V2", "V3", "V4", "V5", "V6", "V7"]
BOULDER_WEIGHTS = [0.05, 0.1, 0.15, 0.2, 0.2, 0.15, 0.1, 0.05]
ROUTE_GRADES = ["5.9", "5.10a", "5.10b", "5.10c", "5.10d", "5.11a", "5.11b", "5.11c"]
ROUTE_WEIGHTS = [0.08, 0.14, 0.18, 0.2, 0.16, 0.12, 0.08, 0.04]

NOTES = [
    "Felt strong on the top-out.", "Slipped on the start twice before it went.",
    "Beta from a friend unlocked the crux.", "Skin was trashed by the end.",
    "Need more core tension for the roof section.", "Flowed first try, felt easy for the grade.",
    "Heel hook is the key.", "Pumped out at the anchors.", None, None, None,
]


def seed() -> None:
    random.seed(42)
    db = SessionLocal()
    try:
        if db.scalar(select(User).where(User.email == DEMO_EMAIL)) is not None:
            print(f"Demo user {DEMO_EMAIL} already exists - nothing to do.")
            return

        user = User(
            email=DEMO_EMAIL,
            password_hash=hash_password(DEMO_PASSWORD),
            display_name="Demo Climber",
            climbing_style="boulder",
            home_gym="Boulder Barn",
            grade_range_boulder="V4-V6",
            grade_range_route="5.10d-5.11b",
            goals="Send V7 outdoors by end of season; build finger strength.",
        )
        db.add(user)
        db.flush()

        today = date.today()
        start = today - timedelta(days=180)

        # ~45 climbs over the last 6 months
        used_names: set[str] = set()
        for _ in range(45):
            is_boulder = random.random() < 0.75
            climbed_on = start + timedelta(days=random.randint(0, 179))
            outdoor = random.random() < 0.25
            if is_boulder:
                grade = random.choices(BOULDER_GRADES, BOULDER_WEIGHTS)[0]
                name = random.choice(BOULDER_NAMES)
                climb_type, grade_system = "boulder", "v_scale"
            else:
                grade = random.choices(ROUTE_GRADES, ROUTE_WEIGHTS)[0]
                name = random.choice(ROUTE_NAMES)
                climb_type, grade_system = "sport", "yds"
            if name in used_names:
                name = f"{name} ({grade})"
            used_names.add(name)

            hardness = (BOULDER_GRADES.index(grade) / 7) if is_boulder else (
                ROUTE_GRADES.index(grade) / 7
            )
            if random.random() < max(0.05, 0.55 - hardness * 0.5):
                send_type = "flash" if is_boulder else "onsight"
                attempt_count = 1
            elif random.random() < 0.85 - hardness * 0.3:
                send_type = "redpoint"
                attempt_count = random.randint(2, 3 + int(hardness * 8))
            else:
                send_type = "project"
                attempt_count = random.randint(2, 10)

            db.add(
                Climb(
                    user_id=user.id,
                    name=name,
                    grade=grade,
                    grade_system=grade_system,
                    climb_type=climb_type,
                    wall_angle=random.choices(ANGLES, ANGLE_WEIGHTS)[0],
                    location=random.choice(OUTDOOR_LOCATIONS if outdoor else GYM_LOCATIONS),
                    send_type=send_type,
                    attempt_count=attempt_count,
                    notes=random.choice(NOTES),
                    climbed_on=climbed_on,
                )
            )

        # ~2-3 sessions a week over the same period
        day = start
        while day <= today:
            if day.weekday() in (1, 3) or (day.weekday() == 5 and random.random() < 0.7):
                session_type = random.choices(
                    ["gym", "board", "outdoor", "hangboard"], [0.45, 0.25, 0.15, 0.15]
                )[0]
                duration = {
                    "gym": random.randint(90, 150),
                    "board": random.randint(60, 90),
                    "outdoor": random.randint(180, 300),
                    "hangboard": random.randint(30, 50),
                }[session_type]
                details = None
                if session_type == "hangboard":
                    details = [
                        {"exercise": "hangboard", "detail": "20mm 7/3 repeaters", "sets": 6},
                        {"exercise": "hangboard", "detail": "15mm max hangs 10s", "sets": 4},
                    ]
                elif session_type == "board":
                    details = [
                        {"exercise": "campus", "detail": "1-4-7 ladders", "sets": 3},
                    ]
                db.add(
                    TrainingSession(
                        user_id=user.id,
                        session_date=day,
                        session_type=session_type,
                        duration_minutes=duration,
                        rpe=random.randint(5, 9),
                        notes=None,
                        workout_details=details,
                    )
                )
            day += timedelta(days=1)

        db.commit()
        climb_count = len(db.scalars(select(Climb).where(Climb.user_id == user.id)).all())
        session_count = len(
            db.scalars(
                select(TrainingSession).where(TrainingSession.user_id == user.id)
            ).all()
        )
        print(
            f"Seeded {DEMO_EMAIL} (password: {DEMO_PASSWORD}) with "
            f"{climb_count} climbs and {session_count} sessions."
        )
    finally:
        db.close()


if __name__ == "__main__":
    seed()
