import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.job import Job
from app.services.storage import Storage


class JobContext:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        storage: Storage,
        llm_client: Any,
        job: Job,
    ):
        self.session_factory = session_factory
        self.storage = storage
        self.llm_client = llm_client
        self.job = job
        self._cancel_requested = job.cancel_requested

    @property
    def job_id(self) -> uuid.UUID:
        return self.job.id

    @property
    def deck_id(self) -> uuid.UUID:
        return self.job.deck_id

    @property
    def slide_id(self) -> uuid.UUID | None:
        return self.job.slide_id

    @property
    def payload(self) -> dict[str, Any]:
        return self.job.payload

    async def is_cancelled(self) -> bool:
        """Check whether cancellation was requested for this job."""
        if self._cancel_requested:
            return True
        async with self.session_factory() as session:
            db_job = await session.get(Job, self.job.id)
            if db_job and db_job.cancel_requested:
                self._cancel_requested = True
                return True
        return False

    async def progress(self, data: dict[str, Any]) -> None:
        """Update job.progress in the database and bump updated_at."""
        now = datetime.now(UTC)
        self.job.progress = data
        self.job.updated_at = now
        async with self.session_factory() as session:
            async with session.begin():
                stmt = (
                    update(Job)
                    .where(Job.id == self.job.id)
                    .values(
                        progress=data,
                        updated_at=now,
                    )
                )
                await session.execute(stmt)


JobHandler = Callable[[JobContext], Any]
