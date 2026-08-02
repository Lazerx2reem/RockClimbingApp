"""Direction tests for the pure metrics engine.

Builds two hand-crafted tracks — a clean, efficient climb and a sloppy one —
and asserts the engine scores them in the expected direction. No MediaPipe,
no video. Runnable directly (``python -m tests.test_metrics``) or via pytest.
"""
import math

import pytest

from app.analysis.landmarks import Frame, Track
from app.analysis.metrics import InsufficientPoseData, compute_metrics

N = 40
FPS = 10.0


def _frame(hip_x, hip_y, sho_x, wrist_x, ankle_l, ankle_r) -> Frame:
    return {
        "l_hip": [hip_x - 0.05, hip_y, 1.0],
        "r_hip": [hip_x + 0.05, hip_y, 1.0],
        "l_shoulder": [sho_x - 0.05, hip_y - 0.2, 1.0],
        "r_shoulder": [sho_x + 0.05, hip_y - 0.2, 1.0],
        "l_wrist": [wrist_x - 0.02, hip_y - 0.15, 1.0],
        "r_wrist": [wrist_x + 0.02, hip_y - 0.15, 1.0],
        "l_ankle": [ankle_l[0], ankle_l[1], 1.0],
        "r_ankle": [ankle_r[0], ankle_r[1], 1.0],
    }


def good_track() -> Track:
    """Hips on the contact line, smooth ascent, planted feet, upright torso."""
    track = []
    for i in range(N):
        prog = i / (N - 1)
        hip_y = 0.72 - 0.32 * prog  # steady rise
        track.append(
            _frame(
                hip_x=0.5,
                hip_y=hip_y,
                sho_x=0.5,
                wrist_x=0.5,
                ankle_l=(0.47, 0.95),  # planted
                ankle_r=(0.53, 0.95),
            )
        )
    return track


def bad_track() -> Track:
    """Hips swinging off the wall, bouncing, wobbling torso, feet flying around."""
    track = []
    for i in range(N):
        prog = i / (N - 1)
        hip_y = 0.72 - 0.32 * prog + 0.06 * math.sin(i * 2.7)  # bounce
        hip_x = 0.5 + 0.25 * math.sin(i * 1.3)  # swings off the contact line
        sho_x = 0.5 + 0.1 * math.sin(i * 1.9)  # torso wobble
        jump = 0.1 * (1 if i % 2 == 0 else -1)  # feet jumping frame to frame
        track.append(
            _frame(
                hip_x=hip_x,
                hip_y=hip_y,
                sho_x=sho_x,
                wrist_x=0.5,
                ankle_l=(0.47 + jump, 0.95 - jump),
                ankle_r=(0.53 - jump, 0.95 + jump),
            )
        )
    return track


def test_good_scores_high():
    result = compute_metrics(good_track(), FPS)
    assert result["overall_score"] >= 80, result["overall_score"]


def test_bad_scores_low():
    result = compute_metrics(bad_track(), FPS)
    assert result["overall_score"] <= 55, result["overall_score"]


def test_good_beats_bad_on_every_metric():
    good = compute_metrics(good_track(), FPS)["metrics"]
    bad = compute_metrics(bad_track(), FPS)["metrics"]
    for key in good:
        assert good[key]["score"] >= bad[key]["score"], key


def test_feedback_worst_first():
    fb = compute_metrics(bad_track(), FPS)["feedback"]
    severities = [f["severity"] for f in fb]
    rank = {"poor": 0, "warn": 1, "good": 2}
    assert severities == sorted(severities, key=lambda s: rank[s])
    assert len(fb) == 4


def test_insufficient_data_raises():
    with pytest.raises(InsufficientPoseData):
        compute_metrics(good_track()[:3], FPS)


if __name__ == "__main__":
    good = compute_metrics(good_track(), FPS)
    bad = compute_metrics(bad_track(), FPS)
    print(f"good overall={good['overall_score']}  bad overall={bad['overall_score']}")
    for key in good["metrics"]:
        print(
            f"  {key:16s} good={good['metrics'][key]['score']:3d}"
            f"  bad={bad['metrics'][key]['score']:3d}"
        )
    test_good_scores_high()
    test_bad_scores_low()
    test_good_beats_bad_on_every_metric()
    test_feedback_worst_first()
    test_insufficient_data_raises()
    print("ALL METRICS TESTS PASSED")
