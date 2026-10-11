import os
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# Set test environment if not already set
os.environ.setdefault("ENV", "dev")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/slides_test"
)
os.environ.setdefault(
    "TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/slides_test"
)
os.environ.setdefault("STORAGE_DIR", "./storage_test")

from app.config import settings
from app.db import get_db
from app.main import app


def pytest_addoption(parser):
    parser.addoption(
        "--update-golden",
        action="store_true",
        default=False,
        help="Update golden skeleton snapshot files",
    )


@pytest.fixture(scope="session", autouse=True)
def run_migrations():
    backend_dir = Path(__file__).parent.parent
    alembic_cfg = Config(str(backend_dir / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(backend_dir / "migrations"))
    alembic_cfg.set_main_option("sqlalchemy.url", settings.TEST_DATABASE_URL)
    command.upgrade(alembic_cfg, "head")
    yield


@pytest_asyncio.fixture
async def test_engine():
    engine = create_async_engine(
        settings.TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def clean_database(test_engine):
    tables = [
        "llm_call",
        "deck_revision",
        "slide_version",
        "slide",
        "plan",
        "resource_image",
        "resource",
        "asset",
        "deck",
    ]
    async with test_engine.begin() as conn:
        for t in tables:
            await conn.execute(text(f"TRUNCATE TABLE {t} CASCADE;"))
    yield


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(test_engine) -> AsyncGenerator[AsyncClient, None]:
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
