import os
import random

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..analysis.service import analyze_synthetic, run_analysis
from ..auth import get_current_user
from ..config import settings
from ..database import get_db
from ..models import Climb, Video
from ..schemas import VideoDetailOut, VideoOut
from ..storage import new_storage_key, storage

router = APIRouter(prefix="/videos", tags=["videos"])


def _get_owned_video(video_id: int, user, db: Session) -> Video:
    video = db.get(Video, video_id)
    if video is None or video.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    return video


def _verify_climb(climb_id: int | None, user, db: Session) -> None:
    if climb_id is None:
        return
    climb = db.get(Climb, climb_id)
    if climb is None or climb.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Climb not found")


@router.get("", response_model=list[VideoOut])
def list_videos(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Video]:
    query = (
        select(Video)
        .where(Video.user_id == user.id)
        .order_by(Video.created_at.desc(), Video.id.desc())
    )
    return list(db.scalars(query))


@router.post("", response_model=VideoOut, status_code=status.HTTP_201_CREATED)
def upload_video(
    background: BackgroundTasks,
    file: UploadFile = File(...),
    climb_id: int | None = Form(default=None),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Video:
    if file.content_type not in settings.allowed_video_types:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported type {file.content_type!r}. "
            f"Allowed: {', '.join(settings.allowed_video_types)}",
        )
    _verify_climb(climb_id, user, db)

    key = new_storage_key(file.filename or "upload.mp4")
    size = storage.save(key, file.file)

    max_bytes = settings.max_upload_mb * 1024 * 1024
    if size > max_bytes:
        storage.delete(key)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Video exceeds {settings.max_upload_mb} MB limit.",
        )

    video = Video(
        user_id=user.id,
        climb_id=climb_id,
        original_filename=file.filename or "upload.mp4",
        storage_key=key,
        content_type=file.content_type,
        size_bytes=size,
        status="uploaded",
    )
    db.add(video)
    db.commit()
    db.refresh(video)

    # Pose analysis runs after the response is sent.
    background.add_task(run_analysis, video.id)
    return video


@router.post("/sample", response_model=VideoDetailOut, status_code=status.HTTP_201_CREATED)
def create_sample_video(
    skill: float | None = Query(default=None, ge=0.0, le=1.0),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Video:
    """Create a synthetic, already-analyzed video so the analysis UI is testable
    without shooting and uploading a real climbing clip."""
    seed = random.randint(0, 10_000)
    video = Video(
        user_id=user.id,
        original_filename=f"sample-climb-{seed}.mp4",
        storage_key=new_storage_key("sample.mp4"),
        content_type="video/mp4",
        size_bytes=0,
        status="uploaded",
    )
    db.add(video)
    db.flush()
    analyze_synthetic(db, video, seed=seed, skill=skill)
    db.refresh(video)
    return video


@router.get("/{video_id}", response_model=VideoDetailOut)
def get_video(
    video_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Video:
    return _get_owned_video(video_id, user, db)


@router.get("/{video_id}/file")
def stream_video(
    video_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    video = _get_owned_video(video_id, user, db)
    get_path = getattr(storage, "path", None)
    if get_path is None:
        raise HTTPException(status_code=501, detail="Streaming not supported for this backend")
    path = get_path(video.storage_key)
    if not os.path.exists(path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No media file (this is a sample or the file is missing).",
        )
    # FileResponse handles HTTP Range requests, so the browser can seek.
    return FileResponse(path, media_type=video.content_type, filename=video.original_filename)


@router.post("/{video_id}/reanalyze", response_model=VideoOut)
def reanalyze_video(
    video_id: int,
    background: BackgroundTasks,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Video:
    video = _get_owned_video(video_id, user, db)
    if not storage.exists(video.storage_key):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No media file to re-analyze (sample video).",
        )
    video.status = "uploaded"
    db.commit()
    db.refresh(video)
    background.add_task(run_analysis, video.id)
    return video


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_video(
    video_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    video = _get_owned_video(video_id, user, db)
    storage.delete(video.storage_key)
    db.delete(video)
    db.commit()
