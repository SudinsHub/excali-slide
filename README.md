# Excalidraw Slide Studio

An AI-powered presentation slide studio where every slide is an editable Excalidraw scene.

## Prerequisites

- Python 3.12+ and `uv`
- Node.js 20+ and `npm`
- Docker and Docker Compose (for PostgreSQL)

## Quick Start (Docker - All-in-One)

The fastest way to run the entire stack (PostgreSQL, Backend with automatic migrations, and Frontend):

```bash
docker compose up --build
```

- **Frontend**: [http://localhost:5173](http://localhost:5173)
- **Backend API**: [http://localhost:8000](http://localhost:8000) (Health check: [http://localhost:8000/health](http://localhost:8000/health))
- **PostgreSQL**: `localhost:5432` (Databases: `slides`, `slides_test`)

> **Note**: Database migrations (`alembic upgrade head`) run automatically on backend container startup. Hot-reload is enabled for both backend and frontend via volume mounts.

---

### Alternative: Local Development (Without Docker for Apps)

If you prefer running Python and Node directly on your host machine (using Docker only for PostgreSQL):

```bash
# 1. Start Database
docker compose up -d postgres

# 2. Backend Setup
cd backend
cp ../.env.example .env
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000

# 3. Frontend Setup (in a separate terminal)
cd frontend
npm install
npm run dev
```

## Running Tests

### In Docker
```bash
docker compose exec backend uv run pytest
docker compose exec frontend npm test -- --run
```

### Or Locally
```bash
# Backend
cd backend && uv run pytest

# Frontend
cd frontend && npm test
```

## Linting & Formatting
```bash
cd backend
uv run ruff check .
uv run ruff format --check .

cd frontend
npm run lint
```
