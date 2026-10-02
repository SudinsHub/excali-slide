.PHONY: dev test lint migrate

dev:
	docker compose up -d
	cd backend && uv run uvicorn app.main:app --reload --port 8000 &
	cd frontend && npm run dev

test:
	cd backend && uv run pytest
	cd frontend && npm test

lint:
	cd backend && uv run ruff check . && uv run ruff format --check .
	cd frontend && npm run lint

migrate:
	cd backend && uv run alembic upgrade head
