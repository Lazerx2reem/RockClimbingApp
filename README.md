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

### 1. Database

```bash
docker compose up -d db
```

### 2. Backend (http://localhost:8000)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head          # apply migrations
python -m app.seed            # optional: demo user + realistic mock data
uvicorn app.main:app --reload
```

API docs at http://localhost:8000/docs.

### 3. Frontend (http://localhost:3000)

```bash
cd frontend
npm install
npm run dev
```

### Demo login (after seeding)

- email: `demo@ascent.app`
- password: `demo1234`

## Configuration

Backend reads `.env` (see `backend/.env.example`): `DATABASE_URL`, `JWT_SECRET`.
Frontend reads `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000`).
