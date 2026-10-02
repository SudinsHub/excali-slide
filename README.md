# Excalidraw Slide Studio

An AI-powered presentation slide studio where every slide is an editable Excalidraw scene.

## Prerequisites

- Python 3.12+ and `uv`
- Node.js 20+ and `npm`
- Docker and Docker Compose (for PostgreSQL)

## Quick Start

### 1. Start Database
```bash
docker compose up -d
```
This runs PostgreSQL on port 5432 with databases `slides` (dev) and `slides_test` (test).

### 2. Backend Setup
```bash
cd backend
cp ../.env.example .env
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

## Running Tests

### Backend
```bash
cd backend
uv run pytest
```

### Frontend
```bash
cd frontend
npm test
```

## Linting & Formatting
```bash
cd backend
uv run ruff check .
uv run ruff format --check .

cd frontend
npm run lint
```
