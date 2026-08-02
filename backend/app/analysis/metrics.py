"""Pure biomechanics metrics computed from a normalized pose track.

These are transparent heuristics, not a calibrated biomechanical model — every
threshold below is a documented, tunable guess. They turn a keypoint track into
four scored movement-quality metrics and ordered coaching feedback:

- hip_position   — how close the hips stay to the wall-contact line (efficiency)
- cog_stability  — how smooth vs. jerky the center-of-gravity path is
- foot_control   — "silent feet": frame-to-frame foot speed (low = controlled)
- body_tension   — torso steadiness and hip bounce (core engagement on steeps)

All distances are normalized by torso length so results are scale-invariant
across camera distances and climbers.
"""
from __future__ import annotations

import statistics
from typing import Optional

from . import landmarks as lm
from .landmarks import Track

MIN_ANALYZABLE_FRAMES = 5


class InsufficientPoseData(Exception):
    """Raised when too few frames contain a detectable climber to analyze."""


def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def _score_lower_better(value: float, good: float, bad: float) -> float:
    """100 when value<=good, 0 when value>=bad, linear between."""
    if value <= good:
        return 100.0
    if value >= bad:
        return 0.0
    return _clamp(100.0 * (bad - value) / (bad - good))


def body_scale(track: Track) -> float:
    """Median torso length across frames — a robust, scale-invariant unit."""
    lengths = [t for f in track if (t := lm.torso_length(f)) is not None and t > 1e-4]
    if not lengths:
        return 0.2  # fallback: ~1/5 of frame height
    return statistics.median(lengths)


def _series(track: Track, fn) -> list:
    """Apply ``fn`` to each frame, keeping only non-None results."""
    return [v for f in track if (v := fn(f)) is not None]


def _hip_position(track: Track, scale: float) -> tuple[float, float]:
    """Mean horizontal hip offset from the contact line, in torso-lengths."""
    offsets = []
    for f in track:
        hip = lm.hip_center(f)
        cx = lm.contact_center_x(f)
        if hip is not None and cx is not None:
            offsets.append(abs(hip[0] - cx) / scale)
    if not offsets:
        return 0.0, 50.0
    value = statistics.mean(offsets)
    return value, _score_lower_better(value, good=0.15, bad=0.6)


def _cog_stability(track: Track, scale: float) -> tuple[float, float]:
    """Jerkiness of the center-of-gravity (hip center) path; lower is smoother."""
    cog = _series(track, lm.hip_center)
    if len(cog) < 3:
        return 0.0, 50.0
    # Second differences ~ acceleration; their magnitude is "jerkiness".
    accels = []
    for i in range(1, len(cog) - 1):
        ax = cog[i - 1][0] - 2 * cog[i][0] + cog[i + 1][0]
        ay = cog[i - 1][1] - 2 * cog[i][1] + cog[i + 1][1]
        accels.append((ax * ax + ay * ay) ** 0.5 / scale)
    value = statistics.mean(accels)
    return value, _score_lower_better(value, good=0.02, bad=0.12)


def _foot_speeds(track: Track, scale: float, fps: float) -> list[float]:
    """Per-frame speed of each foot in torso-lengths per second."""
    speeds: list[float] = []
    dt = 1.0 / fps
    for joint in ("l_ankle", "r_ankle"):
        prev: Optional[lm.Point] = None
        for f in track:
            cur = lm.get(f, joint) or lm.get(f, joint.replace("ankle", "foot"))
            if prev is not None and cur is not None:
                speeds.append((lm.distance(prev, cur) / scale) / dt)
            prev = cur
    return speeds


def _foot_control(track: Track, scale: float, fps: float) -> tuple[float, float]:
    """Silent feet: blend of mean and peak foot speed (both lower = better)."""
    speeds = _foot_speeds(track, scale, fps)
    if not speeds:
        return 0.0, 50.0
    mean_speed = statistics.mean(speeds)
    # 90th percentile as a robust "peak" that ignores single-frame jitter.
    peak = sorted(speeds)[max(0, int(len(speeds) * 0.9) - 1)]
    mean_score = _score_lower_better(mean_speed, good=0.2, bad=1.2)
    peak_score = _score_lower_better(peak, good=1.0, bad=4.0)
    return mean_speed, (mean_score + peak_score) / 2


def _body_tension(track: Track, scale: float) -> tuple[float, float]:
    """Torso-angle steadiness + hip bounce; steadier = more core tension.

    Bounce is measured as the acceleration (second difference) of hip height, not
    its raw spread — so steady upward climbing progress doesn't count against
    tension; only high-frequency wobble does.
    """
    angles = _series(track, lm.torso_angle_deg)
    hips_y = [p[1] for p in _series(track, lm.hip_center)]
    if len(angles) < 3 or len(hips_y) < 3:
        return 0.0, 50.0
    angle_std = statistics.pstdev(angles)
    bounce_accels = [
        abs(hips_y[i - 1] - 2 * hips_y[i] + hips_y[i + 1]) / scale
        for i in range(1, len(hips_y) - 1)
    ]
    bounce = statistics.mean(bounce_accels)
    angle_score = _score_lower_better(angle_std, good=4.0, bad=20.0)
    bounce_score = _score_lower_better(bounce, good=0.01, bad=0.08)
    return angle_std, (angle_score + bounce_score) / 2


# metric key -> (label, unit, weight in the overall score)
_META = {
    "hip_position": ("Hip position", "torso-lengths", 1.0),
    "cog_stability": ("Center-of-gravity control", "accel", 1.0),
    "foot_control": ("Silent feet", "body-lengths/s", 1.0),
    "body_tension": ("Body tension", "degrees", 1.0),
}

_SUMMARY = {
    "hip_position": lambda v: f"Hips sit on average {v:.2f} torso-lengths off the contact line.",
    "cog_stability": lambda v: f"Center-of-gravity jerk averages {v:.3f} per frame.",
    "foot_control": lambda v: f"Feet move at {v:.2f} body-lengths/s on average between placements.",
    "body_tension": lambda v: f"Torso angle varies by {v:.1f}° through the climb.",
}

# severity band -> (title, message) per metric, chosen by score.
_FEEDBACK = {
    "hip_position": {
        "good": ("Hips stay close to the wall", "Efficient — your hips track the contact line, keeping weight over your feet."),
        "warn": ("Hips drift out at times", "On some moves your hips swing away from the wall. Turn a hip in and press through your toes to stay close."),
        "poor": ("Hips held away from the wall", "Your hips sit well off the wall for much of the climb, loading your arms. Drill hip-turns (backstep/drop-knee) to bring your center in."),
    },
    "cog_stability": {
        "good": ("Smooth center of gravity", "Your weight moves in a controlled, continuous path between holds."),
        "warn": ("Some abrupt weight shifts", "A few moves show jerky center-of-gravity shifts. Initiate from the legs and move more deliberately into each hold."),
        "poor": ("Jerky, lurching movement", "Your center of gravity lurches between positions, which wastes energy and reduces control. Slow down and lead with the hips."),
    },
    "foot_control": {
        "good": ("Quiet, precise feet", "Great footwork — feet land softly and stay put, a hallmark of efficient climbing."),
        "warn": ("Feet a little busy", "Feet reposition faster than ideal on some moves. Place once, look before you step, and trust the foot."),
        "poor": ("Sloppy, noisy feet", "Feet are cutting and re-adjusting frequently. Practice silent-feet drills: place each foot deliberately and keep it still."),
    },
    "body_tension": {
        "good": ("Strong body tension", "Your torso stays steady with minimal bounce — solid core engagement, especially useful on steeps."),
        "warn": ("Tension drops on some moves", "Your torso wobbles through parts of the climb. Engage your core and squeeze feet into the wall to keep tension."),
        "poor": ("Losing body tension", "The torso swings and hips bounce, a sign of leaking tension. Core and hip-flexor strength plus tension drills on overhangs will help."),
    },
}


def _severity(score: float) -> str:
    if score >= 80:
        return "good"
    if score >= 60:
        return "warn"
    return "poor"


def compute_metrics(track: Track, fps: float) -> dict:
    """Turn a pose track into scored metrics, feedback, and an overall score.

    Raises ``InsufficientPoseData`` if too few frames contain a climber.
    """
    usable = sum(1 for f in track if lm.hip_center(f) is not None)
    if usable < MIN_ANALYZABLE_FRAMES:
        raise InsufficientPoseData(
            f"only {usable} frames with a detectable climber "
            f"(need {MIN_ANALYZABLE_FRAMES})"
        )

    scale = body_scale(track)
    computed = {
        "hip_position": _hip_position(track, scale),
        "cog_stability": _cog_stability(track, scale),
        "foot_control": _foot_control(track, scale, fps),
        "body_tension": _body_tension(track, scale),
    }

    metrics: dict[str, dict] = {}
    for key, (value, score) in computed.items():
        label, unit, _ = _META[key]
        metrics[key] = {
            "key": key,
            "label": label,
            "value": round(value, 3),
            "unit": unit,
            "score": round(score),
            "summary": _SUMMARY[key](value),
        }

    total_weight = sum(w for _, _, w in _META.values())
    overall = round(
        sum(metrics[k]["score"] * _META[k][2] for k in metrics) / total_weight
    )

    # Feedback: worst metrics first so the most useful coaching leads.
    severity_rank = {"poor": 0, "warn": 1, "good": 2}
    feedback = []
    for key in sorted(metrics, key=lambda k: metrics[k]["score"]):
        sev = _severity(metrics[key]["score"])
        title, message = _FEEDBACK[key][sev]
        feedback.append(
            {
                "category": key,
                "severity": sev,
                "title": title,
                "message": message,
                "score": metrics[key]["score"],
            }
        )
    feedback.sort(key=lambda f: severity_rank[f["severity"]])

    return {"metrics": metrics, "feedback": feedback, "overall_score": overall}
