"""Initial schema: users, climbs, attempts, training_sessions

Revision ID: 0001
Revises:
Create Date: 2026-07-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("climbing_style", sa.String(50), nullable=True),
        sa.Column("home_gym", sa.String(120), nullable=True),
        sa.Column("grade_range_boulder", sa.String(20), nullable=True),
        sa.Column("grade_range_route", sa.String(20), nullable=True),
        sa.Column("goals", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "climbs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("grade", sa.String(10), nullable=False),
        sa.Column("grade_system", sa.String(10), nullable=False),
        sa.Column("climb_type", sa.String(10), nullable=False),
        sa.Column("wall_angle", sa.String(10), nullable=True),
        sa.Column("location", sa.String(120), nullable=True),
        sa.Column("send_type", sa.String(10), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("climbed_on", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_climbs_user_id", "climbs", ["user_id"])

    op.create_table(
        "attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "climb_id",
            sa.Integer(),
            sa.ForeignKey("climbs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("attempt_date", sa.Date(), nullable=False),
        sa.Column("outcome", sa.String(10), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_attempts_climb_id", "attempts", ["climb_id"])
    op.create_index("ix_attempts_user_id", "attempts", ["user_id"])

    op.create_table(
        "training_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("session_date", sa.Date(), nullable=False),
        sa.Column("session_type", sa.String(20), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("rpe", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("workout_details", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_training_sessions_user_id", "training_sessions", ["user_id"])


def downgrade() -> None:
    op.drop_table("training_sessions")
    op.drop_table("attempts")
    op.drop_table("climbs")
    op.drop_table("users")
