#!/bin/sh
set -e

echo "Waiting for database connection..."
until uv run python -c "
import asyncio, sys
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import settings

async def check():
    try:
        engine = create_async_engine(settings.DATABASE_URL)
        async with engine.connect() as conn:
            pass
        await engine.dispose()
        sys.exit(0)
    except Exception as e:
        sys.exit(1)

asyncio.run(check())
"; do
  echo "PostgreSQL is not ready yet - retrying in 1s..."
  sleep 1
done

echo "PostgreSQL is ready."
echo "Applying database migrations..."
uv run alembic upgrade head
echo "Database migrations applied successfully."

echo "Executing command: $@"
exec "$@"
