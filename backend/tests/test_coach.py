"""Coach tests: the tool layer, the prompt builder, and the conversation API.

The tools are exercised against a real session rather than mocks — they are the
part that must never leak another athlete's data, and that guarantee only means
something against actual queries.
"""
import json
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.coach.prompt import build_system_prompt
from app.coach.tools import run_tool
from app.database import SessionLocal
from app.main import app
from app.models import User

client = TestClient(app)


def _auth(email: str) -> dict:
    r = client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "display_name": "Coachee"},
    )
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _climb(headers: dict, **overrides) -> int:
    payload = {
        "name": "Test problem",
        "grade": "V4",
        "grade_system": "v_scale",
        "climb_type": "boulder",
        "wall_angle": "overhang",
        "send_type": "redpoint",
        "attempt_count": 3,
        "climbed_on": date.today().isoformat(),
    }
    payload.update(overrides)
    r = client.post("/climbs", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _session(headers: dict, **overrides) -> int:
    payload = {
        "session_date": date.today().isoformat(),
        "session_type": "hangboard",
        "duration_minutes": 60,
        "rpe": 7,
    }
    payload.update(overrides)
    r = client.post("/sessions", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _user(email: str) -> User:
    with SessionLocal() as db:
        return db.scalar(select(User).where(User.email == email))


def _call(name: str, args: dict, email: str) -> dict:
    """Run a tool the way the service does and parse its JSON result."""
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        return json.loads(run_tool(name, args, user, db))


# ---------- Prompt ----------


def test_prompt_includes_filled_profile_fields_only():
    prompt = build_system_prompt(
        {
            "display_name": "Robyn",
            "climbing_style": "boulder",
            "home_gym": None,
            "grade_range_boulder": "V5-V7",
            "grade_range_route": None,
            "goals": "Send my first V8",
        },
        date(2026, 8, 6),
    )
    assert "Robyn" in prompt
    assert "V5-V7" in prompt
    assert "Send my first V8" in prompt
    assert "Home gym" not in prompt  # empty fields are omitted, not left blank
    assert "2026-08-06" in prompt


def test_prompt_handles_an_empty_profile():
    prompt = build_system_prompt({}, date(2026, 8, 6))
    assert "no profile details filled in yet" in prompt


# ---------- Tools ----------


def test_training_summary_reports_totals_and_recent_window():
    email = "summary@test.dev"
    h = _auth(email)
    _climb(h, grade="V4")
    _climb(h, grade="V6", send_type="flash")
    _climb(h, grade="V7", send_type="project")  # unsent — not a send
    _session(h, duration_minutes=90, rpe=8)

    result = _call("get_training_summary", {"days": 30}, email)

    assert result["all_time"]["climbs_logged"] == 3
    assert result["all_time"]["sends"] == 2
    assert result["all_time"]["hardest_boulder"] == "V6"
    assert result["all_time"]["hours"] == 1.5
    assert result["last_30_days"]["sessions"] == 1
    assert result["last_30_days"]["avg_rpe"] == 8.0


def test_recent_climbs_filters_and_returns_notes():
    email = "climbs@test.dev"
    h = _auth(email)
    _climb(h, name="Sent one", grade="V3", send_type="flash")
    _climb(h, name="Open project", grade="V8", send_type="project", notes="Crux throw")

    projects = _call("get_recent_climbs", {"send_type": "project"}, email)
    assert projects["count"] == 1
    assert projects["climbs"][0]["name"] == "Open project"
    assert projects["climbs"][0]["notes"] == "Crux throw"

    routes = _call("get_recent_climbs", {"climb_type": "sport"}, email)
    assert routes["count"] == 0


def test_recent_climbs_limit_is_clamped_not_trusted():
    email = "clamp@test.dev"
    h = _auth(email)
    for _ in range(3):
        _climb(h)

    # A nonsense limit from the model must not blow up or return everything.
    assert _call("get_recent_climbs", {"limit": "lots"}, email)["count"] == 3
    assert _call("get_recent_climbs", {"limit": -5}, email)["count"] == 1
    assert _call("get_recent_climbs", {"limit": 99999}, email)["count"] == 3


def test_grade_pyramid_is_ordered_hardest_first():
    email = "pyramid@test.dev"
    h = _auth(email)
    _climb(h, grade="V3", send_type="flash")
    _climb(h, grade="V5", send_type="redpoint")
    _climb(h, grade="V3", send_type="repeat")

    pyramid = _call("get_grade_pyramid", {"discipline": "boulder"}, email)["pyramid"]
    assert [entry["grade"] for entry in pyramid] == ["V5", "V3"]
    assert pyramid[1]["sends"] == 2


def test_recent_sessions_returns_workout_detail():
    email = "sessions@test.dev"
    h = _auth(email)
    _session(
        h,
        session_type="hangboard",
        workout_details=[{"exercise": "hangboard", "detail": "20mm 7/3", "sets": 6}],
    )
    _session(h, session_type="gym", duration_minutes=120)

    hangboard = _call("get_recent_sessions", {"session_type": "hangboard"}, email)
    assert hangboard["count"] == 1
    assert hangboard["sessions"][0]["workout"][0]["detail"] == "20mm 7/3"


def test_video_analysis_tools_expose_scores_and_feedback():
    email = "video@test.dev"
    h = _auth(email)
    video_id = client.post("/videos/sample", headers=h).json()["id"]

    listed = _call("list_video_analyses", {}, email)
    assert listed["count"] == 1
    row = listed["videos"][0]
    assert row["video_id"] == video_id
    assert row["is_sample"] is True
    assert set(row["scores"]) == {
        "hip_position",
        "cog_stability",
        "foot_control",
        "body_tension",
    }

    detail = _call("get_video_analysis", {"video_id": video_id}, email)
    assert detail["overall_score"] == row["overall_score"]
    assert len(detail["feedback"]) == 4


def test_tools_never_reach_another_athletes_data():
    owner_email = "tool-owner@test.dev"
    other_email = "tool-other@test.dev"
    owner = _auth(owner_email)
    _auth(other_email)
    _climb(owner, name="Owner's project")
    video_id = client.post("/videos/sample", headers=owner).json()["id"]

    assert _call("get_recent_climbs", {}, other_email)["count"] == 0
    assert _call("list_video_analyses", {}, other_email)["count"] == 0
    # Guessing a video id gets an error, not someone else's analysis.
    assert "error" in _call("get_video_analysis", {"video_id": video_id}, other_email)


def test_unknown_tool_returns_an_error_the_model_can_read():
    email = "unknown@test.dev"
    _auth(email)
    assert "error" in _call("get_secret_plans", {}, email)


# ---------- Conversation API ----------


def test_conversation_crud_and_ownership():
    h1 = _auth("convo-owner@test.dev")
    h2 = _auth("convo-intruder@test.dev")

    created = client.post("/coach/conversations", json={}, headers=h1)
    assert created.status_code == 201, created.text
    convo_id = created.json()["id"]
    assert created.json()["messages"] == []

    assert any(c["id"] == convo_id for c in client.get("/coach/conversations", headers=h1).json())
    assert client.get("/coach/conversations", headers=h2).json() == []

    # A second user can neither read nor delete it.
    assert client.get(f"/coach/conversations/{convo_id}", headers=h2).status_code == 404
    assert client.delete(f"/coach/conversations/{convo_id}", headers=h2).status_code == 404

    assert client.delete(f"/coach/conversations/{convo_id}", headers=h1).status_code == 204
    assert client.get(f"/coach/conversations/{convo_id}", headers=h1).status_code == 404


def test_conversations_require_auth():
    assert client.get("/coach/conversations").status_code == 401


def test_sending_a_message_without_an_api_key_returns_503(monkeypatch):
    from app.config import settings

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(settings, "anthropic_api_key", None)

    h = _auth("no-key@test.dev")
    convo_id = client.post("/coach/conversations", json={}, headers=h).json()["id"]

    r = client.post(
        f"/coach/conversations/{convo_id}/messages",
        json={"content": "How am I doing?"},
        headers=h,
    )
    assert r.status_code == 503
    assert "ANTHROPIC_API_KEY" in r.json()["detail"]
    # The turn is rejected before anything is written to the transcript.
    assert client.get(f"/coach/conversations/{convo_id}", headers=h).json()["messages"] == []


def test_status_reports_configuration(monkeypatch):
    from app.config import settings

    h = _auth("status@test.dev")

    monkeypatch.setattr(settings, "anthropic_api_key", "sk-ant-test")
    assert client.get("/coach/status", headers=h).json()["available"] is True

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(settings, "anthropic_api_key", None)
    assert client.get("/coach/status", headers=h).json()["available"] is False


# ---------- Streaming turn ----------
#
# The model call itself is faked: these cover our SSE framing, transcript
# persistence, and history assembly, none of which need a real API key.


def _frames(body: str) -> list[dict]:
    return [
        json.loads(line[len("data: ") :])
        for line in body.splitlines()
        if line.startswith("data: ")
    ]


def _fake_turn(events):
    """Build a stream_reply stand-in that records the history it was handed."""
    seen: dict = {}

    def fake(user, db, history):
        seen["history"] = history
        yield from events

    return fake, seen


def test_streamed_turn_is_framed_and_persisted(monkeypatch):
    import app.routers.coach as coach_router

    events = [
        {"type": "tool", "name": "get_recent_climbs"},
        {"type": "delta", "text": "You've been "},
        {"type": "delta", "text": "climbing well."},
        {
            "type": "complete",
            "text": "You've been climbing well.",
            "tool_calls": [{"name": "get_recent_climbs", "input": {"days": 30}}],
        },
    ]
    fake, seen = _fake_turn(events)
    monkeypatch.setattr(coach_router, "coach_available", lambda: True)
    monkeypatch.setattr(coach_router, "stream_reply", fake)

    h = _auth("stream@test.dev")
    convo_id = client.post("/coach/conversations", json={}, headers=h).json()["id"]

    r = client.post(
        f"/coach/conversations/{convo_id}/messages",
        json={"content": "How was my month?"},
        headers=h,
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")

    frames = _frames(r.text)
    assert [f["type"] for f in frames] == ["tool", "delta", "delta", "done"]
    assert frames[0]["name"] == "get_recent_climbs"

    # The turn the model saw ends with the user's message.
    assert seen["history"][-1] == {"role": "user", "content": "How was my month?"}

    convo = client.get(f"/coach/conversations/{convo_id}", headers=h).json()
    assert convo["title"] == "How was my month?"  # derived from the first message
    assert [m["role"] for m in convo["messages"]] == ["user", "assistant"]
    assistant = convo["messages"][1]
    assert assistant["id"] == frames[-1]["message_id"]
    assert assistant["content"] == "You've been climbing well."
    assert assistant["tool_calls"] == [
        {"name": "get_recent_climbs", "input": {"days": 30}}
    ]


def test_second_turn_replays_the_whole_transcript(monkeypatch):
    import app.routers.coach as coach_router

    fake, seen = _fake_turn(
        [{"type": "complete", "text": "Noted.", "tool_calls": []}]
    )
    monkeypatch.setattr(coach_router, "coach_available", lambda: True)
    monkeypatch.setattr(coach_router, "stream_reply", fake)

    h = _auth("multiturn@test.dev")
    convo_id = client.post("/coach/conversations", json={}, headers=h).json()["id"]
    for text in ("First question", "Second question"):
        client.post(
            f"/coach/conversations/{convo_id}/messages",
            json={"content": text},
            headers=h,
        )

    assert seen["history"] == [
        {"role": "user", "content": "First question"},
        {"role": "assistant", "content": "Noted."},
        {"role": "user", "content": "Second question"},
    ]
    # The title stays anchored to the first message, not the latest one.
    assert client.get(f"/coach/conversations/{convo_id}", headers=h).json()["title"] == (
        "First question"
    )


def test_a_failed_turn_writes_no_assistant_message(monkeypatch):
    import app.routers.coach as coach_router

    fake, _ = _fake_turn(
        [
            {"type": "delta", "text": "partial"},
            {"type": "error", "message": "The coach hit an unexpected error."},
        ]
    )
    monkeypatch.setattr(coach_router, "coach_available", lambda: True)
    monkeypatch.setattr(coach_router, "stream_reply", fake)

    h = _auth("failed-turn@test.dev")
    convo_id = client.post("/coach/conversations", json={}, headers=h).json()["id"]
    r = client.post(
        f"/coach/conversations/{convo_id}/messages",
        json={"content": "Anything"},
        headers=h,
    )

    assert _frames(r.text)[-1]["type"] == "error"
    convo = client.get(f"/coach/conversations/{convo_id}", headers=h).json()
    assert [m["role"] for m in convo["messages"]] == ["user"]


def test_blank_content_is_rejected_before_the_coach_is_reached():
    h = _auth("empty@test.dev")
    convo_id = client.post("/coach/conversations", json={}, headers=h).json()["id"]
    r = client.post(
        f"/coach/conversations/{convo_id}/messages", json={"content": ""}, headers=h
    )
    assert r.status_code == 422  # schema validation runs ahead of the endpoint body


@pytest.mark.parametrize(
    "content,expected",
    [
        ("Short question?", "Short question?"),
        ("  spaced   out  words ", "spaced out words"),
    ],
)
def test_title_is_derived_from_the_first_message(content, expected):
    from app.routers.coach import _derive_title

    assert _derive_title(content) == expected


def test_long_titles_are_truncated():
    from app.routers.coach import TITLE_LENGTH, _derive_title

    title = _derive_title("word " * 100)
    assert len(title) == TITLE_LENGTH
    assert title.endswith("…")
