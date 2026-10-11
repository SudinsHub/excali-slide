from pathlib import Path
from typing import Any

import jinja2

from app.config import settings
from app.ir.schemas import Plan
from app.llm.client import LLMClient, get_llm_client

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(str(PROMPTS_DIR)),
    autoescape=False,
    trim_blocks=True,
    lstrip_blocks=True,
)


def _diagram_share_label(intensity: str) -> str:
    intensity = (intensity or "medium").lower()
    if intensity == "low":
        return "~25%"
    elif intensity == "high":
        return "~75%"
    return "~50%"


async def generate_plan(
    deck: Any,
    resources: list[Any],
    images: list[Any],
    feedback: str | None = None,
    previous: Plan | None = None,
    client: LLMClient | None = None,
) -> Plan:
    """Generate a structured presentation plan from deck settings, resources, and image catalog."""
    llm = client or get_llm_client()
    deck_settings = getattr(deck, "settings", {}) or {}

    target_count = deck_settings.get("slide_count")
    slide_count_label = f"{target_count} slides" if target_count else "6-12 slides (auto)"
    tone = deck_settings.get("tone", "professional")
    diagram_intensity = deck_settings.get("diagram_intensity", "medium")
    density = deck_settings.get("density", "standard")
    audience = deck_settings.get("audience", "general audience")
    extra_instructions = deck_settings.get("extra_instructions", "")

    sys_tmpl = jinja_env.get_template("planner_system.md.j2")
    system_prompt = sys_tmpl.render(
        diagram_share=_diagram_share_label(diagram_intensity),
        tone=tone,
        audience=audience,
        density=density,
        extra_instructions=extra_instructions,
    )

    # Prepare resources representation
    res_list = []
    for r in resources:
        res_text = getattr(r, "text", "") or ""
        # Cap resource text if excessively large
        if len(res_text) > settings.MAX_RESOURCE_CHARS:
            res_text = res_text[: settings.MAX_RESOURCE_CHARS] + "\n...[truncated]"
        res_list.append(
            {
                "id": str(getattr(r, "id", "")),
                "filename": getattr(r, "filename", "unnamed"),
                "text": res_text,
            }
        )

    # Prepare images catalog
    img_list = []
    for img in images:
        img_list.append(
            {
                "asset_id": str(getattr(img, "asset_id", getattr(img, "id", ""))),
                "caption": getattr(img, "caption", ""),
                "kind": getattr(img, "kind", "other"),
                "locator": getattr(img, "locator", ""),
            }
        )

    user_tmpl = jinja_env.get_template("planner_user.md.j2")
    user_prompt = user_tmpl.render(
        brief=getattr(deck, "title", "Presentation Brief"),
        slide_count_label=slide_count_label,
        tone=tone,
        diagram_intensity=diagram_intensity,
        density=density,
        audience=audience,
        extra_instructions=extra_instructions,
        resources=res_list,
        images=img_list,
        previous_plan=previous.model_dump_json(indent=2) if previous else None,
        feedback=feedback,
    )

    plan = await llm.structured_call(
        model=settings.LLM_MODEL_PLANNER,
        system=system_prompt,
        user=user_prompt,
        schema=Plan,
        purpose="planner",
    )

    # Post-process Plan:
    # 1. Enforce slide_count (keep within +-1 if target is specified)
    if target_count and isinstance(target_count, int):
        if len(plan.slides) > target_count + 1:
            plan.slides = plan.slides[: target_count + 1]
        elif len(plan.slides) < max(1, target_count - 1):
            # If model returned too few, keep as is (cannot invent without hallucinating)
            pass

    # 2. Assign stable keys: s1..sN
    for i, slide in enumerate(plan.slides, start=1):
        slide.key = f"s{i}"

    # 3. Drop image_ids that do not exist
    available_asset_ids = {str(item["asset_id"]) for item in img_list}
    for slide in plan.slides:
        slide.image_ids = [aid for aid in slide.image_ids if aid in available_asset_ids]

    # 4. Validate source_refs
    available_resource_ids = {str(item["id"]) for item in res_list}
    for slide in plan.slides:
        slide.source_refs = [
            ref for ref in slide.source_refs if str(ref.resource_id) in available_resource_ids
        ]

    return plan
