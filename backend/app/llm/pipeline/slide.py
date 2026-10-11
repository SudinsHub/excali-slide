from pathlib import Path
from typing import Any

import jinja2

from app.compiler import CompileCtx, CompileResult, compile
from app.config import settings
from app.errors import GenerationError
from app.ir.budgets import budgets_for
from app.ir.schemas import Plan, PlanSlide, SlideIR
from app.llm.client import LLMClient, get_llm_client
from app.schemas.deck import DeckSettings

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(str(PROMPTS_DIR)),
    autoescape=False,
    trim_blocks=True,
    lstrip_blocks=True,
)


async def generate_slide(
    deck: Any,
    plan: Plan,
    plan_slide: PlanSlide,
    images: list[Any] | None = None,
    resources: list[Any] | None = None,
    client: LLMClient | None = None,
    compile_ctx: CompileCtx | None = None,
) -> tuple[SlideIR, CompileResult]:
    """Generate a SlideIR for a single planned slide, validate and compile to Excalidraw skeleton."""
    llm = client or get_llm_client()
    raw_settings = getattr(deck, "settings", {}) or {}
    try:
        deck_settings = DeckSettings(**raw_settings)
    except Exception:
        deck_settings = DeckSettings()

    budgets = budgets_for(deck_settings)
    tone = deck_settings.tone
    density = deck_settings.density
    brief = getattr(deck, "title", "Presentation Brief")

    sys_tmpl = jinja_env.get_template("slide_system.md.j2")
    system_prompt = sys_tmpl.render(
        max_nodes=budgets.max_nodes,
        bullets=budgets.bullets,
        words=budgets.words_per_bullet,
    )

    plan_outline = [
        {
            "key": s.key,
            "role": s.role,
            "kind": s.kind,
            "title": s.title,
            "intent": s.intent,
        }
        for s in plan.slides
    ]

    # Filter images attached to this slide
    all_images = images or []
    slide_image_ids = set(plan_slide.image_ids)
    slide_images = [
        {
            "asset_id": str(getattr(img, "asset_id", getattr(img, "id", ""))),
            "caption": getattr(img, "caption", ""),
            "kind": getattr(img, "kind", "other"),
        }
        for img in all_images
        if str(getattr(img, "asset_id", getattr(img, "id", ""))) in slide_image_ids
    ]

    # Assemble source excerpts (capped at 12k chars)
    excerpt_parts: list[str] = []
    current_chars = 0
    for r in resources or []:
        txt = getattr(r, "text", "") or ""
        if not txt:
            continue
        remaining = 12000 - current_chars
        if remaining <= 0:
            break
        snippet = txt[:remaining]
        excerpt_parts.append(f"[{getattr(r, 'filename', 'source')}]: {snippet}")
        current_chars += len(snippet)
    source_excerpts = "\n\n".join(excerpt_parts) if excerpt_parts else "(No source notes available)"

    user_tmpl = jinja_env.get_template("slide_user.md.j2")
    issues: list[dict[str, str]] | None = None

    max_rounds = 2  # initial + 1 extra repair round
    last_compile_result: CompileResult | None = None

    for _round_idx in range(max_rounds):
        user_prompt = user_tmpl.render(
            brief=brief,
            tone=tone,
            density=density,
            plan_outline=plan_outline,
            plan_slide_json=plan_slide.model_dump_json(indent=2),
            glossary=[g.model_dump() for g in plan.glossary],
            slide_images=slide_images,
            source_excerpts=source_excerpts,
            issues=issues,
        )

        ir = await llm.structured_call(
            model=settings.LLM_MODEL_SLIDE,
            system=system_prompt,
            user=user_prompt,
            schema=SlideIR,
            purpose="slide",
        )
        # Ensure slide_key matches the planned slide
        ir.slide_key = plan_slide.key

        compile_result = compile(ir, compile_ctx)
        last_compile_result = compile_result

        if not compile_result.errors:
            # Succeeded compilation!
            return ir, compile_result

        # Format compile errors for the repair round
        issues = [
            {"code": "compile_error", "path": "ir", "message": err} for err in compile_result.errors
        ]

    # If compilation still failed after repair round, raise GenerationError
    err_msgs = last_compile_result.errors if last_compile_result else ["Unknown compilation error"]
    raise GenerationError(
        message=f"Slide compilation failed for '{plan_slide.title}': {'; '.join(err_msgs)}",
        issues=err_msgs,
    )
