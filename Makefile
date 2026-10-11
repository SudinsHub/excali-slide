.PHONY: dev test lint migrate worker down logs

dev:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

worker:
	docker compose up -d worker

migrate:
	docker compose exec backend uv run alembic upgrade head

test-backend:
	docker compose exec backend uv run pytest

test-frontend:
	docker compose exec frontend npm test -- --run

test: test-backend test-frontend

lint-backend:
	docker compose exec backend uv run ruff check .
	docker compose exec backend uv run ruff format --check .

lint-frontend:
	docker compose exec frontend npm run lint

lint: lint-backend lint-frontend
