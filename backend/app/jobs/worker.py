import asyncio
import logging
import signal
import uuid
from typing import Any

import app.jobs.handlers  # noqa: F401
from app.config import settings
from app.db import async_session_factory
from app.jobs.context import JobContext
from app.jobs.queue import claim, complete, fail, heartbeat, is_retryable_error, reap_stale
from app.jobs.registry import HANDLERS
from app.models.job import Job
from app.services.storage import storage

logger = logging.getLogger("worker")


class Worker:
    def __init__(
        self,
        worker_id: str | None = None,
        concurrency: int | None = None,
        poll_interval: float = 1.0,
        busy_poll_interval: float = 0.1,
    ):
        self.worker_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
        self.concurrency = concurrency or settings.JOB_CONCURRENCY
        self.poll_interval = poll_interval
        self.busy_poll_interval = busy_poll_interval
        self.running = False
        self.active_tasks: dict[uuid.UUID, asyncio.Task] = {}
        self.active_jobs: dict[uuid.UUID, Job] = {}
        self.semaphore = asyncio.Semaphore(self.concurrency)
        self._llm_client: Any = None

    @property
    def llm_client(self) -> Any:
        if self._llm_client is None:
            from app.llm.client import get_llm_client

            self._llm_client = get_llm_client()
        return self._llm_client

    async def _execute_job(self, job: Job) -> None:
        job_id = job.id
        self.active_jobs[job_id] = job
        logger.info(f"Worker {self.worker_id} started job {job_id} ({job.kind})")

        ctx = JobContext(
            session_factory=async_session_factory,
            storage=storage,
            llm_client=self.llm_client,
            job=job,
        )

        handler_fn = HANDLERS.get(job.kind)
        if not handler_fn:
            err = f"No handler registered for job kind '{job.kind}'"
            logger.error(err)
            async with async_session_factory() as session:
                async with session.begin():
                    await fail(session, job_id, err, retryable=False)
            self.active_jobs.pop(job_id, None)
            return

        try:
            # Check cancellation before starting
            if await ctx.is_cancelled():
                logger.info(f"Job {job_id} cancelled before execution")
                return

            result = await handler_fn(ctx)

            async with async_session_factory() as session:
                async with session.begin():
                    await complete(session, job_id, result if isinstance(result, dict) else None)
            logger.info(f"Worker {self.worker_id} completed job {job_id} ({job.kind})")

        except asyncio.CancelledError:
            logger.warning(f"Job {job_id} task was cancelled")
            async with async_session_factory() as session:
                async with session.begin():
                    await fail(session, job_id, "Job execution cancelled", retryable=True)
            raise
        except Exception as exc:
            retryable = is_retryable_error(exc)
            err_msg = str(exc) or exc.__class__.__name__
            logger.exception(f"Job {job_id} failed: {err_msg} (retryable={retryable})")
            async with async_session_factory() as session:
                async with session.begin():
                    await fail(session, job_id, err_msg, retryable=retryable)
        finally:
            self.active_jobs.pop(job_id, None)
            self.semaphore.release()

    async def _heartbeat_loop(self) -> None:
        while self.running:
            try:
                await asyncio.sleep(15)
                if not self.running:
                    break
                job_ids = list(self.active_jobs.keys())
                if job_ids:
                    async with async_session_factory() as session:
                        async with session.begin():
                            for jid in job_ids:
                                await heartbeat(session, jid, self.worker_id)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Heartbeat loop error: {e}")

    async def _reaper_loop(self) -> None:
        while self.running:
            try:
                await asyncio.sleep(30)
                if not self.running:
                    break
                async with async_session_factory() as session:
                    async with session.begin():
                        reaped = await reap_stale(session, stale_after_s=90)
                        if reaped:
                            logger.info(f"Reaped {len(reaped)} stale jobs")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Reaper loop error: {e}")

    async def run(self) -> None:
        self.running = True
        logger.info(f"Worker {self.worker_id} started (concurrency={self.concurrency})")

        # Import handlers to register them
        try:
            import app.jobs.handlers  # noqa: F401
        except ImportError:
            pass

        heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        reaper_task = asyncio.create_task(self._reaper_loop())

        try:
            while self.running:
                # Calculate available concurrency slots
                free_slots = self.concurrency - len(self.active_jobs)
                if free_slots <= 0:
                    await asyncio.sleep(self.busy_poll_interval)
                    continue

                claimed_jobs: list[Job] = []
                try:
                    async with async_session_factory() as session:
                        async with session.begin():
                            claimed_jobs = await claim(session, self.worker_id, n=free_slots)
                except Exception as e:
                    logger.error(f"Error claiming jobs: {e}")
                    await asyncio.sleep(self.poll_interval)
                    continue

                if claimed_jobs:
                    for job in claimed_jobs:
                        await self.semaphore.acquire()
                        task = asyncio.create_task(self._execute_job(job))
                        self.active_tasks[job.id] = task

                        def _cleanup(t: asyncio.Task, jid=job.id):
                            self.active_tasks.pop(jid, None)

                        task.add_done_callback(_cleanup)

                    await asyncio.sleep(self.busy_poll_interval)
                else:
                    await asyncio.sleep(self.poll_interval)

        finally:
            self.running = False
            heartbeat_task.cancel()
            reaper_task.cancel()

            # Wait for active tasks or timeout
            if self.active_tasks:
                logger.info(f"Waiting for {len(self.active_tasks)} active jobs to complete...")
                await asyncio.gather(*self.active_tasks.values(), return_exceptions=True)
            logger.info(f"Worker {self.worker_id} shutdown clean.")

    def stop(self) -> None:
        self.running = False


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    )
    worker = Worker()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, worker.stop)
        except NotImplementedError:
            # Signal handling might differ on non-POSIX, but inside Linux docker it works
            pass

    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
