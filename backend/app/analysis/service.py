"""Orchestrates a video's analysis: extract -> compute -> persist.

Called as a FastAPI background task after upload, so it manages its own DB
session. A synthetic path (no real video) backs demo/sample analyses and dev
testing. Both paths share the same persistence + metrics code, so a synthetic
result is structurally identical to a real one.
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import PoseAnalysis, Video
from ..storage import storage
from .landmarks import Track
from .metrics import InsufficientPoseData, compute_metrics

logger = logging.getLogger(__name__)

# Keypoint frames are downsampled to at most this many before storing, keeping
# the JSON small while leaving enough to redraw the skeleton / compare beta.
MAX_STORED_FRAMES = 120


def _downsample(track: Track, limit: int = MAX_STORED_FRAMES) -> Track:
    if len(track) <= limit:
        return track
    step = len(track) / limit
    return [track[int(i * step)] for i in range(limit)]


def _persist(db: Session, video: Video, track: Track, meta: dict) -> PoseAnalysis:
    """Compute metrics for a track and write the analysis + video metadata."""
    result = compute_metrics(track, meta["analyzed_fps"])

    video.duration_seconds = meta.get("duration_seconds")
    video.fps = meta.get("analyzed_fps")
    video.width = meta.get("width")
    video.height = meta.get("height")
    video.status = "analyzed"
    video.error_message = None

    analysis = PoseAnalysis(
        video_id=video.id,
        user_id=video.user_id,
        frame_count=meta["frame_count"],
        analyzed_fps=meta["analyzed_fps"],
        overall_score=result["overall_score"],
        keypoints=_downsample(track),
        metrics=result["metrics"],
        feedback=result["feedback"],
        source=meta.get("source", "mediapipe"),
    )
    # Replace any prior analysis (re-run).
    if video.analysis is not None:
        db.delete(video.analysis)
        db.flush()
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis


def run_analysis(video_id: int) -> None:
    """Background entry point: analyze an uploaded video by id."""
    from .extractor import VideoDecodeError, extract_track  # lazy: needs OpenCV

    db = SessionLocal()
    try:
        video = db.get(Video, video_id)
        if video is None:
            logger.warning("run_analysis: video %s vanished", video_id)
            return
        video.status = "processing"
        db.commit()

        try:
            with storage.local_path(video.storage_key) as path:
                track, meta = extract_track(path)
            _persist(db, video, track, meta)
            logger.info("Analyzed video %s (%s frames)", video_id, meta["frame_count"])
        except (VideoDecodeError, InsufficientPoseData) as exc:
            video.status = "failed"
            video.error_message = str(exc)
            db.commit()
            logger.info("Analysis failed for video %s: %s", video_id, exc)
        except Exception as exc:  # noqa: BLE001 — never leave a video stuck "processing"
            video.status = "failed"
            video.error_message = f"unexpected error: {exc}"
            db.commit()
            logger.exception("Unexpected analysis error for video %s", video_id)
    finally:
        db.close()


def analyze_synthetic(db: Session, video: Video, seed: int, skill: float | None) -> PoseAnalysis:
    """Attach a synthetic analysis to a video (demo/sample/dev). Caller commits scope."""
    from .synthetic import synthetic_track

    track, meta = synthetic_track(seed=seed, skill=skill)
    return _persist(db, video, track, meta)
