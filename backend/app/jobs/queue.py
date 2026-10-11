import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job


def is_retryable_error(exc: Exception) -> bool:
    """Determine if an exception is retryable according to the pipeline retry policy.

    Retryable: LiteLLM rate limit, timeout, connection, 5xx HTTP.
    Non-retryable: validation exhaustion, BadRequest, GenerationError, etc.
    """
    name = exc.__class__.__name__
    msg = str(exc).lower()

    # Explicit non-retryable errors
    if name in ("GenerationError", "ValidationError", "JSONDecodeError"):
        return False
    if "validation" in msg or "budget" in msg or "non-retryable" in msg:
        return False

    status_code = getattr(exc, "status_code", None)
    if status_code in (429, 500, 502, 503, 504):
        return True

    retryable_name_parts = (
        "ratelimit",
        "timeout",
        "connection",
        "serviceunavailable",
        "internalserver",
    )
    if any(part in name.lower() for part in retryable_name_parts):
        return True

    if any(
        k in msg
        for k in (
            "rate limit",
            "timed out",
            "timeout",
            "connection refused",
            "503 service unavailable",
            "502 bad gateway",
        )
    ):
        return True

    return False


async def enqueue(
    session: AsyncSession,
    kind: str,
    deck_id: uuid.UUID,
    slide_id: uuid.UUID | None = None,
    payload: dict[str, Any] | None = None,
    priority: int = 0,
    run_after: datetime | None = None,
) -> Job:
    """Enqueue a new job with status='queued'."""
    job = Job(
        deck_id=deck_id,
        slide_id=slide_id,
        kind=kind,
        status="queued",
        priority=priority,
        payload=payload or {},
        progress={},
        attempts=0,
        run_after=run_after,
    )
    session.add(job)
    await session.flush()
    return job


async def claim(
    session: AsyncSession,
    worker_id: str,
    n: int = 1,
) -> list[Job]:
    """Atomically claim up to n queued jobs using FOR UPDATE SKIP LOCKED ordered by priority DESC, created_at ASC."""
    if n <= 0:
        return []

    now = datetime.now(UTC)
    claimed_cte = (
        select(Job.id)
        .where(
            Job.status == "queued",
            or_(Job.run_after.is_(None), Job.run_after <= now),
        )
        .order_by(Job.priority.desc(), Job.created_at.asc())
        .limit(n)
        .with_for_update(skip_locked=True)
        .cte("claimed")
    )

    stmt = (
        update(Job)
        .where(Job.id == claimed_cte.c.id)
        .values(
            status="running",
            locked_by=worker_id,
            locked_at=now,
            started_at=func.coalesce(Job.started_at, now),
            attempts=Job.attempts + 1,
            updated_at=now,
        )
        .returning(Job)
    )

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def complete(
    session: AsyncSession,
    job_id: uuid.UUID,
    result: dict[str, Any] | None = None,
) -> Job | None:
    """Mark a job as succeeded."""
    now = datetime.now(UTC)
    stmt = (
        update(Job)
        .where(Job.id == job_id)
        .values(
            status="succeeded",
            result=result or {},
            locked_by=None,
            locked_at=None,
            finished_at=now,
            updated_at=now,
        )
        .returning(Job)
    )
    res = await session.execute(stmt)
    return res.scalar_one_or_none()


async def fail(
    session: AsyncSession,
    job_id: uuid.UUID,
    error: str,
    retryable: bool = False,
) -> Job | None:
    """Fail or retry a job according to retryable status and attempt count."""
    job = await session.get(Job, job_id)
    if not job:
        return None

    now = datetime.now(UTC)
    if retryable and job.attempts < job.max_attempts:
        backoff_seconds = 3 * (2**job.attempts)
        job.status = "queued"
        job.run_after = now + timedelta(seconds=backoff_seconds)
        job.error = error
        job.locked_by = None
        job.locked_at = None
        job.updated_at = now
    else:
        job.status = "failed"
        job.error = error
        job.finished_at = now
        job.locked_by = None
        job.locked_at = None
        job.updated_at = now

    await session.flush()
    return job


async def heartbeat(
    session: AsyncSession,
    job_id: uuid.UUID,
    worker_id: str,
) -> bool:
    """Update locked_at timestamp for an active job."""
    now = datetime.now(UTC)
    stmt = (
        update(Job)
        .where(
            Job.id == job_id,
            Job.locked_by == worker_id,
            Job.status == "running",
        )
        .values(
            locked_at=now,
            updated_at=now,
        )
    )
    res = await session.execute(stmt)
    return res.rowcount > 0


async def cancel(
    session: AsyncSession,
    job_id: uuid.UUID,
) -> Job | None:
    """Cancel a job. If queued, sets status='cancelled'. If running, flags cancel_requested."""
    job = await session.get(Job, job_id)
    if not job:
        return None

    now = datetime.now(UTC)
    if job.status == "queued":
        job.status = "cancelled"
        job.finished_at = now
        job.cancel_requested = True
        job.updated_at = now
    elif job.status == "running":
        job.cancel_requested = True
        job.updated_at = now

    await session.flush()
    return job


async def reap_stale(
    session: AsyncSession,
    stale_after_s: int = 90,
) -> list[Job]:
    """Find running jobs with stale heartbeats and requeue or fail them."""
    now = datetime.now(UTC)
    threshold = now - timedelta(seconds=stale_after_s)

    stmt = select(Job).where(
        Job.status == "running",
        Job.locked_at < threshold,
    )
    result = await session.execute(stmt)
    stale_jobs = list(result.scalars().all())

    reaped: list[Job] = []
    for job in stale_jobs:
        if job.attempts < job.max_attempts:
            backoff_seconds = 3 * (2**job.attempts)
            job.status = "queued"
            job.run_after = now + timedelta(seconds=backoff_seconds)
            job.error = f"Reaped stale job (heartbeat expired, worker was {job.locked_by})"
            job.locked_by = None
            job.locked_at = None
            job.updated_at = now
        else:
            job.status = "failed"
            job.finished_at = now
            job.error = f"Stale job exceeded max attempts (worker was {job.locked_by})"
            job.locked_by = None
            job.locked_at = None
            job.updated_at = now
        reaped.append(job)

    if reaped:
        await session.flush()
    return reaped
