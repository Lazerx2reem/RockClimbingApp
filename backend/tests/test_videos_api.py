"""API tests for the video upload + pose analysis surface (TestClient)."""
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _auth(email: str) -> dict:
    r = client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "display_name": "V"},
    )
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_sample_video_is_analyzed_immediately():
    h = _auth("sample@test.dev")
    r = client.post("/videos/sample?skill=0.85", headers=h)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "analyzed"
    assert body["analysis"]["source"] == "synthetic"
    assert 0 <= body["analysis"]["overall_score"] <= 100
    assert set(body["analysis"]["metrics"]) == {
        "hip_position", "cog_stability", "foot_control", "body_tension"
    }
    assert len(body["analysis"]["feedback"]) == 4


def test_list_and_detail_and_ownership():
    h1 = _auth("owner@test.dev")
    h2 = _auth("intruder@test.dev")
    vid = client.post("/videos/sample", headers=h1).json()["id"]

    listed = client.get("/videos", headers=h1).json()
    assert any(v["id"] == vid for v in listed)
    # List rows carry a compact analysis summary, not the full metrics blob.
    row = next(v for v in listed if v["id"] == vid)
    assert "overall_score" in row["analysis"] and "metrics" not in row["analysis"]

    # A second user can neither see nor fetch it.
    assert client.get("/videos", headers=h2).json() == []
    assert client.get(f"/videos/{vid}", headers=h2).status_code == 404
    # Sample videos have no media file to stream.
    assert client.get(f"/videos/{vid}/file", headers=h1).status_code == 404


def test_upload_rejects_wrong_type():
    h = _auth("badtype@test.dev")
    files = {"file": ("photo.png", b"not-a-video", "image/png")}
    r = client.post("/videos", files=files, headers=h)
    assert r.status_code == 415, r.text


def _tiny_mp4() -> bytes | None:
    """Encode a few frames of noise to mp4; None if no codec is available."""
    import cv2
    import tempfile, os

    path = os.path.join(tempfile.mkdtemp(), "noise.mp4")
    writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), 15, (320, 240))
    if not writer.isOpened():
        return None
    rng = np.random.default_rng(0)
    for _ in range(20):
        writer.write(rng.integers(0, 255, (240, 320, 3), dtype=np.uint8))
    writer.release()
    with open(path, "rb") as f:
        return f.read()


def test_real_upload_decodes_and_fails_gracefully():
    """A decodable video with no detectable climber should end 'failed', not crash.

    TestClient runs the background analysis task before returning, so the final
    status is observable right after upload.
    """
    data = _tiny_mp4()
    if data is None:
        pytest.skip("no mp4 encoder available in this OpenCV build")
    h = _auth("realupload@test.dev")
    files = {"file": ("noise.mp4", data, "video/mp4")}
    r = client.post("/videos", files=files, headers=h)
    assert r.status_code == 201, r.text
    vid = r.json()["id"]

    detail = client.get(f"/videos/{vid}", headers=h).json()
    assert detail["status"] == "failed"
    assert detail["error_message"]  # a human-readable reason is recorded
    assert detail["analysis"] is None


def test_delete_removes_video():
    h = _auth("deleter@test.dev")
    vid = client.post("/videos/sample", headers=h).json()["id"]
    assert client.delete(f"/videos/{vid}", headers=h).status_code == 204
    assert client.get(f"/videos/{vid}", headers=h).status_code == 404
