import uuid

import pytest
from sqlalchemy import select

from app.jobs.context import JobContext
from app.jobs.handlers import (
    handle_generate_plan,
    handle_generate_slide,
    handle_ingest_resource,
)
from app.jobs.queue import claim
from app.llm.client import FakeLLM
from app.models.deck_revision import DeckRevision
from app.models.job import Job
from app.services.storage import storage


async def run_all_jobs(session_factory, max_cycles=10):
    """Helper to drain all queued jobs using registered handlers and FakeLLM."""
    handlers = {
        "ingest_resource": handle_ingest_resource,
        "generate_plan": handle_generate_plan,
        "generate_slide": handle_generate_slide,
    }

    for _ in range(max_cycles):
        claimed = []
        async with session_factory() as session:
            async with session.begin():
                claimed = await claim(session, worker_id="test_worker", n=10)

        if not claimed:
            break

        for job in claimed:
            ctx = JobContext(
                session_factory=session_factory,
                storage=storage,
                llm_client=FakeLLM(),
                job=job,
            )
            fn = handlers.get(job.kind)
            assert fn is not None, f"No handler for {job.kind}"
            await fn(ctx)

            async with session_factory() as session:
                async with session.begin():
                    db_job = await session.get(Job, job.id)
                    db_job.status = "succeeded"
                    db_job.locked_by = None


@pytest.mark.asyncio
async def test_full_state_machine_flow(client, test_engine):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    session_factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)

    # 1. Create deck
    create_resp = await client.post(
        "/api/decks",
        json={"title": "State Machine Deck", "settings": {"slide_count": 4}},
    )
    assert create_resp.status_code == 201
    deck_id = create_resp.json()["id"]

    # 2. Upload resource
    md_content = b"# System Design Notes\nDetailed microservice architecture notes."
    files = [("files", ("notes.md", md_content, "text/markdown"))]
    upload_resp = await client.post(f"/api/decks/{deck_id}/resources", files=files)
    assert upload_resp.status_code == 201
    assert upload_resp.json()[0]["id"] is not None

    # Drain ingest job
    await run_all_jobs(session_factory)

    # Verify resource parsed
    res_list_resp = await client.get(f"/api/decks/{deck_id}/resources")
    assert res_list_resp.status_code == 200
    assert res_list_resp.json()[0]["status"] == "parsed"

    # 3. Generate plan
    gen_plan_resp = await client.post(f"/api/decks/{deck_id}/plan/generate")
    assert gen_plan_resp.status_code == 202
    assert gen_plan_resp.json()["status"] == "planning"

    # Drain planner job
    await run_all_jobs(session_factory)

    # Verify plan review status and plan retrieval
    deck_resp = await client.get(f"/api/decks/{deck_id}")
    assert deck_resp.json()["status"] == "plan_review"
    assert deck_resp.json()["current_plan_id"] is not None

    plan_resp = await client.get(f"/api/decks/{deck_id}/plan")
    assert plan_resp.status_code == 200
    plan_data = plan_resp.json()
    assert len(plan_data["content"]["slides"]) >= 3
    assert plan_data["version"] == 1

    # 4. User edits plan
    plan_content = plan_data["content"]
    plan_content["title"] = "Updated Plan by User"
    put_resp = await client.put(f"/api/decks/{deck_id}/plan", json=plan_content)
    assert put_resp.status_code == 200
    updated_plan = put_resp.json()
    assert updated_plan["version"] == 2
    assert updated_plan["created_by"] == "user"

    # 5. Approve plan
    approve_resp = await client.post(f"/api/decks/{deck_id}/plan/approve")
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "generating"

    # Verify slides created with status queued
    slides_resp = await client.get(f"/api/decks/{deck_id}/slides")
    assert slides_resp.status_code == 200
    slides = slides_resp.json()
    assert len(slides) == len(plan_content["slides"])
    assert all(s["status"] == "queued" for s in slides)

    # 6. Drain slide generation jobs
    await run_all_jobs(session_factory)

    # 7. Verify all slides are ready and deck is ready with initial revision
    deck_after = await client.get(f"/api/decks/{deck_id}")
    assert deck_after.json()["status"] == "ready"

    slides_after = await client.get(f"/api/decks/{deck_id}/slides")
    assert all(s["status"] == "ready" for s in slides_after.json())

    # Check first deck revision
    async with session_factory() as session:
        rev_stmt = select(DeckRevision).where(DeckRevision.deck_id == uuid.UUID(deck_id))
        revisions = list((await session.execute(rev_stmt)).scalars().all())
        assert len(revisions) == 1
        assert revisions[0].origin == "ai_generate"
        assert len(revisions[0].snapshot["order"]) == len(slides)

    # 8. Test regenerating a single slide
    first_slide_id = slides[0]["id"]
    regen_resp = await client.post(f"/api/slides/{first_slide_id}/regenerate")
    assert regen_resp.status_code == 202

    # Verify slide queued
    single_slide = await client.get(f"/api/slides/{first_slide_id}")
    assert single_slide.json()["status"] == "queued"

    # Drain regen job
    await run_all_jobs(session_factory)

    single_slide_after = await client.get(f"/api/slides/{first_slide_id}")
    assert single_slide_after.json()["status"] == "ready"
