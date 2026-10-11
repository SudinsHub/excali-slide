import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from app.jobs.queue import cancel, claim, enqueue, fail, reap_stale
from app.models.deck import Deck


@pytest.mark.asyncio
async def test_queue_claim_concurrency(db_session, test_engine):
    """Verify that multiple concurrent workers never claim the same job."""
    # Create deck
    deck = Deck(title="Concurrency Test Deck", settings={})
    db_session.add(deck)
    await db_session.commit()

    # Enqueue 10 jobs
    for i in range(10):
        await enqueue(db_session, kind="test_job", deck_id=deck.id, payload={"idx": i})
    await db_session.commit()

    # Run two workers claiming jobs concurrently using separate DB sessions
    from sqlalchemy.ext.asyncio import async_sessionmaker

    session_maker = async_sessionmaker(bind=test_engine, expire_on_commit=False)

    async def worker_claim(worker_id: str, count: int) -> list[str]:
        async with session_maker() as session:
            async with session.begin():
                jobs = await claim(session, worker_id, n=count)
                return [str(j.id) for j in jobs]

    results = await asyncio.gather(
        worker_claim("worker_1", 6),
        worker_claim("worker_2", 6),
    )

    claimed_by_w1 = set(results[0])
    claimed_by_w2 = set(results[1])

    # No overlap!
    assert claimed_by_w1.isdisjoint(claimed_by_w2)
    assert len(claimed_by_w1) + len(claimed_by_w2) == 10


@pytest.mark.asyncio
async def test_queue_retry_backoff(db_session):
    """Verify retry policy: exponential backoff until max_attempts is reached."""
    deck = Deck(title="Retry Deck", settings={})
    db_session.add(deck)
    await db_session.commit()

    await enqueue(db_session, kind="retryable_job", deck_id=deck.id)
    await db_session.commit()

    # Worker claims job
    claimed = await claim(db_session, worker_id="worker_a", n=1)
    await db_session.commit()
    assert len(claimed) == 1
    job_id = claimed[0].id
    assert claimed[0].attempts == 1

    # First retryable failure
    now_before = datetime.now(UTC)
    failed_job = await fail(db_session, job_id, error="Transient rate limit", retryable=True)
    await db_session.commit()

    assert failed_job.status == "queued"
    assert failed_job.error == "Transient rate limit"
    assert failed_job.run_after is not None
    # Backoff for attempt 1: 3s * 2^1 = 6s
    assert failed_job.run_after >= now_before + timedelta(seconds=5)

    # Claim again (attempt 2)
    failed_job.run_after = datetime.now(UTC) - timedelta(seconds=1)
    await db_session.commit()
    claimed_2 = await claim(db_session, worker_id="worker_a", n=1)
    await db_session.commit()
    assert claimed_2[0].attempts == 2

    # Fail attempt 2
    failed_job_2 = await fail(db_session, job_id, error="Transient timeout", retryable=True)
    await db_session.commit()
    assert failed_job_2.status == "queued"
    # Backoff for attempt 2: 3s * 2^2 = 12s

    # Claim again (attempt 3 = max_attempts default 3)
    failed_job_2.run_after = datetime.now(UTC) - timedelta(seconds=1)
    await db_session.commit()
    claimed_3 = await claim(db_session, worker_id="worker_a", n=1)
    await db_session.commit()
    assert claimed_3[0].attempts == 3

    # Fail attempt 3: max_attempts reached -> permanent failure
    final_job = await fail(db_session, job_id, error="Exhausted retries", retryable=True)
    await db_session.commit()
    assert final_job.status == "failed"
    assert final_job.finished_at is not None


@pytest.mark.asyncio
async def test_queue_reaper_stale_job(db_session):
    """Verify that reap_stale detects stale worker heartbeats and requeues jobs."""
    deck = Deck(title="Stale Deck", settings={})
    db_session.add(deck)
    await db_session.commit()

    await enqueue(db_session, kind="stale_job", deck_id=deck.id)
    await db_session.commit()

    claimed = await claim(db_session, worker_id="worker_dead", n=1)
    await db_session.commit()
    job_id = claimed[0].id

    # Simulate expired heartbeat 120s ago (> 90s)
    claimed[0].locked_at = datetime.now(UTC) - timedelta(seconds=120)
    await db_session.commit()

    reaped = await reap_stale(db_session, stale_after_s=90)
    await db_session.commit()

    assert len(reaped) == 1
    reaped_job = reaped[0]
    assert reaped_job.id == job_id
    assert reaped_job.status == "queued"
    assert reaped_job.locked_by is None
    assert "Reaped stale job" in reaped_job.error


@pytest.mark.asyncio
async def test_queue_cancellation(db_session):
    """Verify cancellation for queued vs running jobs."""
    deck = Deck(title="Cancel Deck", settings={})
    db_session.add(deck)
    await db_session.commit()

    # 1. Queued job cancel
    job1 = await enqueue(db_session, kind="queued_job", deck_id=deck.id)
    await db_session.commit()

    cancelled1 = await cancel(db_session, job1.id)
    await db_session.commit()
    assert cancelled1.status == "cancelled"
    assert cancelled1.cancel_requested is True

    # 2. Running job cancel
    job2 = await enqueue(db_session, kind="running_job", deck_id=deck.id)
    await db_session.commit()

    await claim(db_session, worker_id="worker_x", n=1)
    await db_session.commit()

    cancelled2 = await cancel(db_session, job2.id)
    await db_session.commit()
    assert cancelled2.status == "running"  # Stays running until next worker checkpoint
    assert cancelled2.cancel_requested is True
