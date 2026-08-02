"""Pose-based movement analysis for climbing videos.

Layering (so the biomechanics logic is testable without MediaPipe or real video):

- ``landmarks``  — joint constants + geometry helpers over a normalized track.
- ``metrics``    — pure functions turning a keypoint track into scored metrics
                   and coaching feedback. No MediaPipe, no OpenCV.
- ``synthetic``  — generates realistic tracks for dev/tests.
- ``extractor``  — MediaPipe Pose over a video file -> a track (lazy import).
- ``service``    — orchestrates extract/compute/persist for a Video row.
"""
