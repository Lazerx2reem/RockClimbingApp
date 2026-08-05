"""Joint constants and geometry helpers over a normalized pose track.

A *track* is a list of *frames*. Each frame is a dict mapping a joint name to
``[x, y, visibility]`` where x/y are normalized image coordinates in ``[0, 1]``
(y increases downward, as in image space) and visibility is MediaPipe's ``0..1``
confidence. Joints below a visibility threshold are treated as missing.
"""
from __future__ import annotations

import math
from typing import Optional

Frame = dict[str, list[float]]
Track = list[Frame]

# MediaPipe Pose landmark indices for the joints we retain.
POSE_INDICES: dict[str, int] = {
    "nose": 0,
    "l_shoulder": 11,
    "r_shoulder": 12,
    "l_elbow": 13,
    "r_elbow": 14,
    "l_wrist": 15,
    "r_wrist": 16,
    "l_hip": 23,
    "r_hip": 24,
    "l_knee": 25,
    "r_knee": 26,
    "l_ankle": 27,
    "r_ankle": 28,
    "l_foot": 31,  # foot index (toe)
    "r_foot": 32,
}

# The four points that typically contact the wall.
CONTACT_JOINTS = ("l_wrist", "r_wrist", "l_ankle", "r_ankle")

MIN_VISIBILITY = 0.3

Point = tuple[float, float]


def get(frame: Frame, name: str, min_vis: float = MIN_VISIBILITY) -> Optional[Point]:
    """Return ``(x, y)`` for a joint if present and confident, else ``None``."""
    v = frame.get(name)
    if v is None:
        return None
    x, y, vis = v[0], v[1], v[2]
    if vis < min_vis:
        return None
    return (x, y)


def midpoint(a: Optional[Point], b: Optional[Point]) -> Optional[Point]:
    """Midpoint of two points; falls back to whichever is present."""
    if a is not None and b is not None:
        return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    return a if a is not None else b


def distance(a: Optional[Point], b: Optional[Point]) -> Optional[float]:
    if a is None or b is None:
        return None
    return math.hypot(a[0] - b[0], a[1] - b[1])


def hip_center(frame: Frame) -> Optional[Point]:
    return midpoint(get(frame, "l_hip"), get(frame, "r_hip"))


def shoulder_center(frame: Frame) -> Optional[Point]:
    return midpoint(get(frame, "l_shoulder"), get(frame, "r_shoulder"))


def torso_length(frame: Frame) -> Optional[float]:
    """Shoulder-center to hip-center distance — our per-frame body scale."""
    return distance(shoulder_center(frame), hip_center(frame))


def contact_center_x(frame: Frame) -> Optional[float]:
    """Mean x of the visible wall-contact joints (the wall-plane proxy)."""
    xs = [p[0] for j in CONTACT_JOINTS if (p := get(frame, j)) is not None]
    return sum(xs) / len(xs) if xs else None


def torso_angle_deg(frame: Frame) -> Optional[float]:
    """Angle of the hip->shoulder vector from vertical, in degrees (0 = upright)."""
    hip = hip_center(frame)
    sho = shoulder_center(frame)
    if hip is None or sho is None:
        return None
    dx = sho[0] - hip[0]
    dy = sho[1] - hip[1]  # negative when shoulders are above hips (image space)
    # Angle from the vertical axis.
    return math.degrees(math.atan2(abs(dx), abs(dy) if dy != 0 else 1e-6))
