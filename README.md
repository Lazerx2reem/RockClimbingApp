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
- [ ] **Phase 2** — video upload + pose-analysis pipeline
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

## Configuration

Backend reads `.env` (see `backend/.env.example`): `DATABASE_URL`, `JWT_SECRET`.
Frontend reads `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000`).
