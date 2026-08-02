"""MediaPipe Pose extraction: a climbing video -> a normalized keypoint track.

MediaPipe and OpenCV are imported lazily inside ``extract_track`` so importing
this module (and booting the app) never requires them — only running a real
analysis does.
"""
from __future__ import annotations

from .landmarks import POSE_INDICES, Frame, Track


class VideoDecodeError(Exception):
    """Raised when the video file can't be opened or contains no frames."""


def _landmarks_to_frame(pose_landmarks) -> Frame:
    """Map a MediaPipe result to our compact per-frame joint dict (or {} if none)."""
    if pose_landmarks is None:
        return {}
    marks = pose_landmarks.landmark
    frame: Frame = {}
    for name, idx in POSE_INDICES.items():
        p = marks[idx]
        frame[name] = [round(p.x, 5), round(p.y, 5), round(p.visibility, 4)]
    return frame


def extract_track(
    video_path: str,
    target_fps: float = 8.0,
    max_frames: int = 600,
) -> tuple[Track, dict]:
    """Run MediaPipe Pose over the video, sampling down to ``target_fps``.

    Returns ``(track, meta)`` where ``track`` has one frame per analyzed sample
    (uniform timing at the analyzed fps; frames with no detected climber are
    empty dicts) and ``meta`` holds probed video metadata.
    """
    import cv2  # noqa: PLC0415 — lazy so the app boots without OpenCV/MediaPipe
    import mediapipe as mp  # noqa: PLC0415

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise VideoDecodeError(f"could not open video: {video_path}")

    src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    if src_fps <= 0:
        src_fps = 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)

    stride = max(1, round(src_fps / target_fps))
    analyzed_fps = src_fps / stride

    track: Track = []
    pose = mp.solutions.pose.Pose(
        model_complexity=1,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    try:
        idx = 0
        while len(track) < max_frames:
            ok, frame = cap.read()
            if not ok:
                break
            if idx % stride == 0:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = pose.process(rgb)
                track.append(_landmarks_to_frame(result.pose_landmarks))
            idx += 1
    finally:
        pose.close()
        cap.release()

    if not track:
        raise VideoDecodeError(f"no frames decoded from: {video_path}")

    duration = total_frames / src_fps if total_frames else len(track) * stride / src_fps
    meta = {
        "analyzed_fps": round(analyzed_fps, 3),
        "source_fps": round(src_fps, 3),
        "frame_count": len(track),
        "width": width,
        "height": height,
        "duration_seconds": round(duration, 2),
        "source": "mediapipe",
    }
    return track, meta
