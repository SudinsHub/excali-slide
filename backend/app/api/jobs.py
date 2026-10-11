import uuid
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.errors import NotFoundError
from app.jobs.queue import cancel
from app.models.job import Job
from app.schemas.job import JobRead

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobRead)
async def get_job_status(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> JobRead:
    job = await db.get(Job, job_id)
    if not job:
        raise NotFoundError("Job not found")
    return JobRead.model_validate(job)


@router.post("/{job_id}/cancel")
async def cancel_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    job = await cancel(db, job_id)
    if not job:
        raise NotFoundError("Job not found")
    await db.commit()
    return {
        "id": str(job.id),
        "status": job.status,
        "cancel_requested": job.cancel_requested,
    }
