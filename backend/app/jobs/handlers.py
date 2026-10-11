import base64
import hashlib
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select

from app.config import settings
from app.ingest.parsers import PARSERS, process_image_bytes
from app.ir.schemas import Plan, PlanSlide
from app.jobs.context import JobContext
from app.jobs.registry import handler
from app.llm.pipeline.plan import generate_plan
from app.llm.pipeline.slide import generate_slide
from app.models.asset import Asset
from app.models.deck import Deck
from app.models.deck_revision import DeckRevision
from app.models.plan import Plan as PlanModel
from app.models.resource import Resource, ResourceImage
from app.models.slide import Slide
from app.models.slide_version import SlideVersion
from app.schemas.caption import ImageCaption

logger = logging.getLogger("jobs.handlers")


@handler("ingest_resource")
async def handle_ingest_resource(ctx: JobContext) -> dict[str, Any]:
    """Ingest an uploaded resource file, extract text and images, and caption images."""
    resource_id = ctx.payload.get("resource_id")
    if not resource_id:
        return {"error": "Missing resource_id in payload"}

    res_uuid = uuid.UUID(resource_id) if isinstance(resource_id, str) else resource_id

    async with ctx.session_factory() as session:
        resource = await session.get(Resource, res_uuid)
        if not resource:
            return {"error": f"Resource {res_uuid} not found"}

        resource.status = "parsing"
        resource.updated_at = datetime.now(UTC)
        await session.commit()

    try:
        # Check cancellation
        if await ctx.is_cancelled():
            return {"cancelled": True}

        file_bytes = ctx.storage.get(resource.storage_key)
        parser_fn = PARSERS.get(resource.kind)
        if not parser_fn:
            raise ValueError(f"No parser available for resource kind '{resource.kind}'")

        extracted_text, raw_images = parser_fn(file_bytes)

        # Truncate text according to MAX_RESOURCE_CHARS
        truncated = False
        if len(extracted_text) > settings.MAX_RESOURCE_CHARS:
            extracted_text = extracted_text[: settings.MAX_RESOURCE_CHARS]
            truncated = True

        # Process and persist images
        min_dim = 200 if resource.kind in ("pdf", "docx", "pptx") else 0
        caption_tmpl = (
            "You are a technical image analyst. You provide concise captions and classifications for images extracted from documents.\n"
            'Output ONLY JSON matching the schema: {"caption": "string (<= 160 chars)", "kind": "photo|screenshot|chart|diagram|logo|other"}.'
        )
        caption_usr = "Analyze the attached image. Describe its essential subject or takeaway in 160 characters or less, and classify its kind."

        async with ctx.session_factory() as session:
            for raw_img_bytes, locator in raw_images:
                if await ctx.is_cancelled():
                    break

                processed = process_image_bytes(raw_img_bytes, min_dim=min_dim)
                if processed is None:
                    continue

                img_data, mime, width, height = processed
                asset_id = hashlib.sha1(img_data).hexdigest()
                storage_key = f"assets/{asset_id}"

                # Store image bytes in storage
                if not ctx.storage.exists(storage_key):
                    ctx.storage.put(storage_key, img_data)

                # Upsert Asset
                existing_asset = await session.get(Asset, asset_id)
                if not existing_asset:
                    asset = Asset(
                        id=asset_id,
                        deck_id=resource.deck_id,
                        storage_key=storage_key,
                        mime=mime,
                        width=width,
                        height=height,
                    )
                    session.add(asset)
                    await session.flush()

                # Generate image caption if vision model or FakeLLM available
                caption_text = f"Extracted figure from {locator}"
                try:
                    data_url = f"data:{mime};base64,{base64.b64encode(img_data).decode('ascii')}"
                    cap_result: ImageCaption = await ctx.llm_client.structured_call(
                        model=settings.LLM_MODEL_VISION,
                        system=caption_tmpl,
                        user=caption_usr,
                        schema=ImageCaption,
                        images=[data_url],
                        purpose="caption",
                        job_id=ctx.job_id,
                    )
                    caption_text = cap_result.caption
                except Exception as cap_err:
                    logger.info(f"Skipping vision captioning for {asset_id}: {cap_err}")

                # Create ResourceImage
                res_img = ResourceImage(
                    resource_id=resource.id,
                    asset_id=asset_id,
                    caption=caption_text,
                    locator=locator,
                )
                session.add(res_img)

            # Update resource with parsed text and status
            db_res = await session.get(Resource, res_uuid)
            if db_res:
                db_res.status = "parsed"
                db_res.text = extracted_text
                db_res.meta = {"truncated": truncated}
                db_res.error = None
                db_res.updated_at = datetime.now(UTC)
            await session.commit()

        return {"status": "parsed", "truncated": truncated, "images_count": len(raw_images)}

    except Exception as exc:
        logger.exception(f"Resource ingestion failed for {res_uuid}: {exc}")
        async with ctx.session_factory() as session:
            db_res = await session.get(Resource, res_uuid)
            if db_res:
                db_res.status = "failed"
                db_res.error = str(exc)
                db_res.updated_at = datetime.now(UTC)
            await session.commit()
        raise


@handler("generate_plan")
async def handle_generate_plan(ctx: JobContext) -> dict[str, Any]:
    """Generate a structured plan for the deck."""
    feedback = ctx.payload.get("feedback")
    prev_plan_id = ctx.payload.get("previous_plan_id")

    try:
        async with ctx.session_factory() as session:
            deck = await session.get(Deck, ctx.deck_id)
            if not deck:
                raise ValueError(f"Deck {ctx.deck_id} not found")

            # Query parsed resources
            res_stmt = select(Resource).where(
                Resource.deck_id == ctx.deck_id,
                Resource.status == "parsed",
            )
            resources = list((await session.execute(res_stmt)).scalars().all())

            # Query resource images
            img_stmt = select(ResourceImage).join(Resource).where(Resource.deck_id == ctx.deck_id)
            images = list((await session.execute(img_stmt)).scalars().all())

            # Previous plan if requested
            previous_plan: Plan | None = None
            if prev_plan_id:
                db_prev = await session.get(PlanModel, uuid.UUID(str(prev_plan_id)))
                if db_prev and db_prev.content:
                    try:
                        previous_plan = Plan.model_validate(db_prev.content)
                    except Exception:
                        pass

            # Generate plan via pipeline
            plan: Plan = await generate_plan(
                deck=deck,
                resources=resources,
                images=images,
                feedback=feedback,
                previous=previous_plan,
                client=ctx.llm_client,
            )

            # Determine next version number
            ver_stmt = select(func.max(PlanModel.version)).where(PlanModel.deck_id == ctx.deck_id)
            max_ver = (await session.execute(ver_stmt)).scalar() or 0
            new_version = max_ver + 1

            new_plan = PlanModel(
                deck_id=ctx.deck_id,
                version=new_version,
                status="draft",
                content=plan.model_dump(),
                created_by="ai",
            )
            session.add(new_plan)
            await session.flush()

            deck.current_plan_id = new_plan.id
            deck.status = "plan_review"
            deck.updated_at = datetime.now(UTC)
            await session.commit()

            return {"plan_id": str(new_plan.id), "version": new_version}

    except Exception as exc:
        logger.exception(f"Plan generation failed for deck {ctx.deck_id}: {exc}")
        async with ctx.session_factory() as session:
            deck = await session.get(Deck, ctx.deck_id)
            if deck and deck.status == "planning":
                deck.status = "failed"
                deck.updated_at = datetime.now(UTC)
                await session.commit()
        raise


@handler("generate_slide")
async def handle_generate_slide(ctx: JobContext) -> dict[str, Any]:
    """Generate a single slide and compile it to an Excalidraw skeleton."""
    slide_id = ctx.slide_id or ctx.payload.get("slide_id")
    if not slide_id:
        raise ValueError("Missing slide_id for generate_slide handler")

    slide_uuid = uuid.UUID(str(slide_id))

    async with ctx.session_factory() as session:
        slide = await session.get(Slide, slide_uuid)
        if not slide:
            raise ValueError(f"Slide {slide_uuid} not found")

        deck = await session.get(Deck, slide.deck_id)
        if not deck:
            raise ValueError(f"Deck {slide.deck_id} not found")

        slide.status = "generating"
        slide.updated_at = datetime.now(UTC)
        await session.commit()

        # Load plan
        if not deck.current_plan_id:
            raise ValueError(f"Deck {deck.id} has no current_plan_id")
        db_plan = await session.get(PlanModel, deck.current_plan_id)
        if not db_plan:
            raise ValueError(f"Plan {deck.current_plan_id} not found")
        plan = Plan.model_validate(db_plan.content)

        # Find plan slide
        plan_slide: PlanSlide | None = None
        for ps in plan.slides:
            if ps.key == slide.plan_key:
                plan_slide = ps
                break
        if not plan_slide:
            # Fallback by position
            idx = min(slide.position, len(plan.slides) - 1)
            plan_slide = plan.slides[idx]

        # Load resources and images
        res_stmt = select(Resource).where(Resource.deck_id == deck.id, Resource.status == "parsed")
        resources = list((await session.execute(res_stmt)).scalars().all())

        img_stmt = select(ResourceImage).join(Resource).where(Resource.deck_id == deck.id)
        images = list((await session.execute(img_stmt)).scalars().all())

    # Pure pipeline execution (outside DB transaction)
    try:
        ir, compile_res = await generate_slide(
            deck=deck,
            plan=plan,
            plan_slide=plan_slide,
            images=images,
            resources=resources,
            client=ctx.llm_client,
        )

        async with ctx.session_factory() as session:
            db_slide = await session.get(Slide, slide_uuid)
            if not db_slide:
                return {"error": "Slide vanished"}

            # Determine next version seq
            seq_stmt = select(func.max(SlideVersion.seq)).where(SlideVersion.slide_id == slide_uuid)
            max_seq = (await session.execute(seq_stmt)).scalar() or 0
            new_seq = max_seq + 1

            new_version = SlideVersion(
                slide_id=slide_uuid,
                seq=new_seq,
                parent_version_id=db_slide.current_version_id,
                origin="ai_generate",
                prompt=None,
                summary=f"AI Generated: {plan_slide.title}",
                ir=ir.model_dump(),
                skeleton=compile_res.skeleton,
                scene=None,
                warnings=compile_res.warnings,
            )
            session.add(new_version)
            await session.flush()

            db_slide.current_version_id = new_version.id
            db_slide.draft_scene = None
            db_slide.status = "ready"
            db_slide.error = None
            db_slide.updated_at = datetime.now(UTC)

            await _check_deck_completion(session, deck.id)
            await session.commit()

        return {"slide_id": str(slide_uuid), "status": "ready"}

    except Exception as exc:
        logger.exception(f"Generation failed for slide {slide_uuid}: {exc}")
        async with ctx.session_factory() as session:
            db_slide = await session.get(Slide, slide_uuid)
            if db_slide:
                db_slide.status = "failed"
                db_slide.error = str(exc)
                db_slide.updated_at = datetime.now(UTC)
                await _check_deck_completion(session, db_slide.deck_id)
            await session.commit()
        raise


async def _check_deck_completion(session: Any, deck_id: uuid.UUID) -> None:
    """If no slides in deck remain queued or generating, update deck status and create initial deck revision."""
    deck = await session.get(Deck, deck_id)
    if not deck:
        return

    slides_stmt = (
        select(Slide)
        .where(
            Slide.deck_id == deck_id,
            Slide.deleted_at.is_(None),
        )
        .order_by(Slide.position.asc())
    )
    slides = list((await session.execute(slides_stmt)).scalars().all())

    pending_slides = [s for s in slides if s.status in ("queued", "generating")]
    if not pending_slides and slides:
        ready_slides = [s for s in slides if s.status == "ready"]
        if not ready_slides:
            deck.status = "failed"
        else:
            deck.status = "ready"
            # Create first deck_revision if not present
            rev_stmt = select(DeckRevision).where(
                DeckRevision.deck_id == deck_id,
                DeckRevision.origin == "ai_generate",
            )
            existing_rev = (await session.execute(rev_stmt)).scalar_one_or_none()
            if not existing_rev:
                max_rev_stmt = select(func.max(DeckRevision.seq)).where(
                    DeckRevision.deck_id == deck_id
                )
                max_rev_seq = (await session.execute(max_rev_stmt)).scalar() or 0
                snapshot = {
                    "order": [str(s.id) for s in slides],
                    "versions": {
                        str(s.id): str(s.current_version_id) for s in slides if s.current_version_id
                    },
                    "deleted": [],
                }
                revision = DeckRevision(
                    deck_id=deck_id,
                    seq=max_rev_seq + 1,
                    label="Initial AI Generation",
                    origin="ai_generate",
                    prompt=None,
                    snapshot=snapshot,
                )
                session.add(revision)

        deck.updated_at = datetime.now(UTC)
