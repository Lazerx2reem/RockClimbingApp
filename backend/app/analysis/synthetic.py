"""Generate realistic synthetic pose tracks for dev, tests, and demo seeding.

Lets the whole analysis feature be exercised end-to-end without a real video
upload (as the project brief calls for). A ``skill`` in ``[0, 1]`` shapes the
movement: high skill = hips on the wall, smooth center of gravity, quiet feet,
steady torso; low skill = the opposite. Deterministic given a seed.
"""
from __future__ import annotations

import math
import random

from .landmarks import Frame, Track


def _frame(hip_x, hip_y, sho_x, wrist_x, ankle_l, ankle_r) -> Frame:
    return {
        "l_hip": [round(hip_x - 0.05, 5), round(hip_y, 5), 1.0],
        "r_hip": [round(hip_x + 0.05, 5), round(hip_y, 5), 1.0],
        "l_shoulder": [round(sho_x - 0.05, 5), round(hip_y - 0.2, 5), 1.0],
        "r_shoulder": [round(sho_x + 0.05, 5), round(hip_y - 0.2, 5), 1.0],
        "l_elbow": [round(sho_x - 0.09, 5), round(hip_y - 0.17, 5), 0.9],
        "r_elbow": [round(sho_x + 0.09, 5), round(hip_y - 0.17, 5), 0.9],
        "l_wrist": [round(wrist_x - 0.03, 5), round(hip_y - 0.16, 5), 1.0],
        "r_wrist": [round(wrist_x + 0.03, 5), round(hip_y - 0.16, 5), 1.0],
        "l_knee": [round(ankle_l[0], 5), round((hip_y + ankle_l[1]) / 2, 5), 0.9],
        "r_knee": [round(ankle_r[0], 5), round((hip_y + ankle_r[1]) / 2, 5), 0.9],
        "l_ankle": [round(ankle_l[0], 5), round(ankle_l[1], 5), 1.0],
        "r_ankle": [round(ankle_r[0], 5), round(ankle_r[1], 5), 1.0],
        "l_foot": [round(ankle_l[0] - 0.01, 5), round(ankle_l[1] + 0.03, 5), 0.8],
        "r_foot": [round(ankle_r[0] + 0.01, 5), round(ankle_r[1] + 0.03, 5), 0.8],
    }


def synthetic_track(
    seed: int = 0,
    frames: int = 48,
    fps: float = 8.0,
    skill: float | None = None,
) -> tuple[Track, dict]:
    """Build a plausible climbing track and its metadata."""
    rng = random.Random(seed)
    if skill is None:
        skill = rng.uniform(0.35, 0.95)
    noise = 1.0 - skill  # 0 = flawless, ~0.65 = sloppy
    phases = [rng.uniform(0, 2 * math.pi) for _ in range(4)]

    # Oscillations run at a realistic climbing tempo (slow); their amplitude —
    # not their frequency — is what skill controls. Feet track the body's ascent
    # continuously rather than teleporting between holds.
    track: Track = []
    for i in range(frames):
        prog = i / (frames - 1)
        hip_y = 0.72 - 0.34 * prog + noise * 0.05 * math.sin(i * 0.9 + phases[0])
        hip_x = 0.5 + noise * 0.28 * math.sin(i * 0.4 + phases[1])
        sho_x = 0.5 + noise * 0.12 * math.sin(i * 0.5 + phases[2])

        foot_drop = prog * 0.30  # feet climb with the body
        ankle_l = (
            0.46 + noise * 0.06 * math.sin(i * 0.6 + phases[3]),
            0.95 - foot_drop + noise * 0.05 * math.sin(i * 0.7 + phases[3]),
        )
        ankle_r = (
            0.54 + noise * 0.06 * math.sin(i * 0.6 + phases[3] + 1.0),
            0.95 - foot_drop + noise * 0.05 * math.sin(i * 0.7 + phases[3] + 1.0),
        )

        track.append(_frame(hip_x, hip_y, sho_x, 0.5, ankle_l, ankle_r))

    meta = {
        "analyzed_fps": fps,
        "source_fps": fps,
        "frame_count": frames,
        "width": 1080,
        "height": 1920,
        "duration_seconds": round(frames / fps, 2),
        "source": "synthetic",
        "skill": round(skill, 2),
    }
    return track, meta
