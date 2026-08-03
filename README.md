# Ascent — AI-Powered Rock Climbing Companion

"Strava meets a climbing coach." Training logs, send tracking, and (coming soon)
AI-powered video analysis of climbing attempts.

## Stack

| Layer    | Tech                                      |
| -------- | ----------------------------------------- |
| Frontend | Next.js + TypeScript + Tailwind CSS       |
| Backend  | FastAPI (Python) + SQLAlchemy + Alembic   |
| Database | PostgreSQL                                |
| AI       | OpenCV + MediaPipe Pose (phase 2), Claude API coach (phase 3) |

## Roadmap

- [x] **Phase 1** — auth, logbook, session tracker, stats dashboard
- [x] **Phase 2** — video upload + pose-analysis pipeline
- [ ] **Phase 3** — AI coach chat
- [ ] **Phase 4** — weakness detection + training plan generator
- [ ] **Phase 5** — stretch features (board import, conditions, community feed)

## Quickstart

### 1. One-time setup

```bash
# Database — either run Postgres via Docker:
docker compose up -d db
# ...or skip Docker and use SQLite for local dev:
echo 'DATABASE_URL=sqlite:///./dev.db' > backend/.env

# Backend deps (3.12: MediaPipe in phase 2 needs <=3.12)
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head          # apply migrations
python -m app.seed            # optional: demo user + realistic mock data
cd ..

# Frontend + root deps
npm install
cd frontend && npm install && cd ..
```

### 2. Run everything

```bash
npm run dev    # FastAPI on :8000 + Next.js on :3000, one terminal
```

API docs at http://localhost:8000/docs, app at http://localhost:3000.
(`npm run dev:api` / `npm run dev:web` still run either half alone.)

### Demo login (after seeding)

- email: `demo@ascent.app`
- password: `demo1234`

## Video analysis (phase 2)

Under **Analysis**, upload a climbing attempt (mp4/mov/webm/mkv). The backend
runs MediaPipe Pose over the clip and scores four movement fundamentals — hip
position relative to the wall, center-of-gravity control, silent feet, and body
tension — each 0–100 with severity-ranked coaching notes. Analysis runs as a
background task; the UI polls until it's ready.

No climbing video handy? Click **Try a sample analysis** (or run the seed) to
generate a synthetic, already-analyzed attempt so the whole flow is testable
without a real upload. The metrics engine (`app/analysis/metrics.py`) is pure
and unit-tested independently of MediaPipe.

```bash
cd backend && .venv/bin/pytest      # metrics + video API tests
```

## Configuration

Backend reads `.env` (see `backend/.env.example`): `DATABASE_URL`, `JWT_SECRET`.
Uploaded videos use a pluggable store — local disk under `media/` in dev
(`STORAGE_BACKEND`, `MEDIA_ROOT`, `MAX_UPLOAD_MB`), S3-shaped for later.
Frontend reads `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000`).
