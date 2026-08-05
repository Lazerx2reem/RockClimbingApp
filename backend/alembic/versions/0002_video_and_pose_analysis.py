"""Add videos and pose_analysis_results tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "videos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "climb_id",
            sa.Integer(),
            sa.ForeignKey("climbs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("storage_key", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(60), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("fps", sa.Float(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(12), nullable=False, server_default="uploaded"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_videos_user_id", "videos", ["user_id"])
    op.create_index("ix_videos_climb_id", "videos", ["climb_id"])
    op.create_index("ix_videos_status", "videos", ["status"])
    op.create_index("uq_videos_storage_key", "videos", ["storage_key"], unique=True)

    op.create_table(
        "pose_analysis_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "video_id",
            sa.Integer(),
            sa.ForeignKey("videos.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("frame_count", sa.Integer(), nullable=False),
        sa.Column("analyzed_fps", sa.Float(), nullable=False),
        sa.Column("overall_score", sa.Integer(), nullable=False),
        sa.Column("keypoints", sa.JSON(), nullable=True),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("feedback", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(12), nullable=False, server_default="mediapipe"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_pose_analysis_results_user_id", "pose_analysis_results", ["user_id"]
    )
    op.create_index(
        "uq_pose_analysis_video_id",
        "pose_analysis_results",
        ["video_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("pose_analysis_results")
    op.drop_table("videos")
