import asyncio
import json
import logging
import time
import uuid
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from app.config import settings
from app.db import async_session_factory
from app.ir.schemas import (
    DiagramBlock,
    Edge,
    GlossaryItem,
    Node,
    Plan,
    PlanSlide,
    SlideIR,
    TextBlock,
)
from app.models.llm_call import LLMCall
from app.schemas.caption import ImageCaption

logger = logging.getLogger("llm.client")
T = TypeVar("T", bound=BaseModel)


class LLMClient(Protocol):
    async def structured_call(
        self,
        model: str,
        system: str,
        user: str,
        schema: type[T],
        images: list[str] | None = None,
        purpose: str = "structured_call",
        job_id: uuid.UUID | None = None,
    ) -> T: ...


async def log_llm_call(
    purpose: str,
    model: str,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    latency_ms: int,
    ok: bool,
    error: str | None = None,
    job_id: uuid.UUID | None = None,
) -> None:
    try:
        async with async_session_factory() as session:
            async with session.begin():
                record = LLMCall(
                    job_id=job_id,
                    purpose=purpose,
                    model=model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    latency_ms=latency_ms,
                    ok=ok,
                    error=error,
                )
                session.add(record)
    except Exception as e:
        logger.warning(f"Failed to record llm_call: {e}")


def _extract_json_text(content: str) -> str:
    """Extract raw JSON from model response text, stripping markdown blocks if present."""
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


class LiteLLMClient:
    async def structured_call(
        self,
        model: str,
        system: str,
        user: str,
        schema: type[T],
        images: list[str] | None = None,
        purpose: str = "structured_call",
        job_id: uuid.UUID | None = None,
    ) -> T:
        import litellm

        user_content: Any = user
        if images:
            user_content = [{"type": "text", "text": user}]
            for img in images:
                user_content.append({"type": "image_url", "image_url": {"url": img}})

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ]

        schema_dict = schema.model_json_schema()
        use_response_format = True
        response_format: dict[str, Any] | None = {
            "type": "json_schema",
            "json_schema": {"name": schema.__name__, "schema": schema_dict},
        }

        max_turns = 3  # initial + up to 2 repairs
        last_error = ""

        for turn in range(max_turns):
            start_time = time.perf_counter()
            call_ok = False
            err_msg: str | None = None
            prompt_tokens: int | None = None
            completion_tokens: int | None = None

            try:
                kwargs: dict[str, Any] = {
                    "model": model,
                    "messages": messages,
                    "timeout": settings.LLM_TIMEOUT_S,
                }
                if use_response_format and response_format:
                    kwargs["response_format"] = response_format

                try:
                    resp = await litellm.acompletion(**kwargs)
                except Exception as rf_err:
                    # If response_format is rejected by provider, fallback to prompt guidance
                    if use_response_format and (
                        "response_format" in str(rf_err).lower() or "schema" in str(rf_err).lower()
                    ):
                        logger.info(
                            f"Provider rejected response_format, falling back to prompt instructions: {rf_err}"
                        )
                        use_response_format = False
                        messages[0]["content"] += (
                            f"\nIMPORTANT: Your response MUST be valid JSON adhering strictly to this JSON Schema:\n{json.dumps(schema_dict)}"
                        )
                        kwargs.pop("response_format", None)
                        resp = await litellm.acompletion(**kwargs)
                    else:
                        raise

                latency_ms = int((time.perf_counter() - start_time) * 1000)
                usage = getattr(resp, "usage", None)
                if usage:
                    prompt_tokens = getattr(usage, "prompt_tokens", None)
                    completion_tokens = getattr(usage, "completion_tokens", None)

                raw_choice = resp.choices[0].message.content or ""
                cleaned = _extract_json_text(raw_choice)
                validated = schema.model_validate_json(cleaned)

                call_ok = True
                await log_llm_call(
                    purpose=purpose,
                    model=model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    latency_ms=latency_ms,
                    ok=True,
                    job_id=job_id,
                )
                return validated

            except (ValidationError, json.JSONDecodeError, Exception) as exc:
                latency_ms = int((time.perf_counter() - start_time) * 1000)
                err_msg = str(exc)
                last_error = err_msg
                await log_llm_call(
                    purpose=purpose,
                    model=model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    latency_ms=latency_ms,
                    ok=False,
                    error=err_msg,
                    job_id=job_id,
                )

                if turn < max_turns - 1:
                    raw_content = ""
                    if "resp" in locals() and hasattr(resp, "choices") and resp.choices:
                        raw_content = resp.choices[0].message.content or ""
                    logger.warning(
                        f"Structured call turn {turn + 1} validation failed, initiating repair turn: {err_msg}"
                    )
                    messages.append({"role": "assistant", "content": raw_content})
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                f"Your previous output was invalid JSON or failed schema validation with these errors:\n"
                                f"{err_msg}\n\n"
                                "Please fix the errors and output ONLY the corrected JSON matching the schema."
                            ),
                        }
                    )
                else:
                    logger.error(f"Structured call exhausted all {max_turns} turns: {err_msg}")
                    raise


class FakeLLM:
    def __init__(
        self,
        simulated_latency: float = 0.0,
        inject_failure: Exception | None = None,
        fail_turns: int = 0,
    ):
        self.simulated_latency = simulated_latency
        self.inject_failure = inject_failure
        self.fail_turns = fail_turns
        self.call_count = 0

    async def structured_call(
        self,
        model: str,
        system: str,
        user: str,
        schema: type[T],
        images: list[str] | None = None,
        purpose: str = "structured_call",
        job_id: uuid.UUID | None = None,
    ) -> T:
        self.call_count += 1
        if self.simulated_latency > 0:
            await asyncio.sleep(self.simulated_latency)

        if self.inject_failure is not None:
            await log_llm_call(
                purpose=purpose,
                model=model,
                prompt_tokens=100,
                completion_tokens=50,
                latency_ms=int(self.simulated_latency * 1000),
                ok=False,
                error=str(self.inject_failure),
                job_id=job_id,
            )
            raise self.inject_failure

        if self.fail_turns > 0:
            self.fail_turns -= 1
            err = "Simulated invalid JSON in FakeLLM repair turn test"
            await log_llm_call(
                purpose=purpose,
                model=model,
                prompt_tokens=100,
                completion_tokens=50,
                latency_ms=int(self.simulated_latency * 1000),
                ok=False,
                error=err,
                job_id=job_id,
            )
            raise ValidationError.from_exception_data(title=schema.__name__, line_errors=[])

        # Generate deterministic mock outputs based on target schema
        result: Any
        if schema == ImageCaption:
            result = ImageCaption(
                caption="Architecture component diagram showing data ingestion pipeline.",
                kind="diagram",
            )
        elif schema == Plan:
            result = self._generate_fake_plan(user)
        elif schema == SlideIR:
            result = self._generate_fake_slide_ir(user)
        else:
            raise ValueError(f"Unsupported schema {schema} in FakeLLM")

        await log_llm_call(
            purpose=purpose,
            model=model,
            prompt_tokens=250,
            completion_tokens=350,
            latency_ms=int(self.simulated_latency * 1000),
            ok=True,
            job_id=job_id,
        )
        return result

    def _generate_fake_plan(self, user_prompt: str) -> Plan:
        return Plan(
            title="System Architecture & Strategy",
            audience="Technical Leadership",
            goal="Present end-to-end scalable architecture and execution plan",
            narrative_summary="Introduces current context, core architecture, key flow stages, and summary recommendations.",
            glossary=[
                GlossaryItem(term="API Gateway", short_label="API Gateway"),
                GlossaryItem(term="Event Bus", short_label="Event Bus"),
                GlossaryItem(term="Worker Node", short_label="Worker"),
            ],
            slides=[
                PlanSlide(
                    key="s1",
                    role="cover",
                    title="Scalable Architecture Blueprint",
                    kind="text",
                    layout_hint="cover",
                    key_points=[],
                    intent="Introduce the presentation and core thesis",
                ),
                PlanSlide(
                    key="s2",
                    role="content",
                    title="Current System Architecture Bottlenecks",
                    kind="text",
                    layout_hint="text",
                    key_points=[
                        "Monolithic coupling increases deployment latency",
                        "Database connection exhaustion under traffic spikes",
                        "Lack of distributed tracing limits observability",
                    ],
                    intent="Highlight existing performance pain points",
                ),
                PlanSlide(
                    key="s3",
                    role="process",
                    title="End-to-End Ingestion Flow Pipeline",
                    kind="diagram",
                    layout_hint="diagram",
                    diagram_hint={
                        "kind": "flow",
                        "description": "Sequential request processing from Gateway through Bus to Workers",
                    },
                    key_points=[
                        "Gateway validates tokens and rate limits requests",
                        "Event bus buffers incoming message bursts",
                        "Worker pool drains queue with auto-scaling",
                    ],
                    intent="Demonstrate message flow through the core decoupled layers",
                ),
                PlanSlide(
                    key="s4",
                    role="closing",
                    title="Execution Roadmap & Next Milestones",
                    kind="text",
                    layout_hint="closing",
                    key_points=[
                        "Deploy managed Event Bus broker in Q1",
                        "Migrate high-volume ingress routes in Q2",
                        "Automate autoscaling policies across workers",
                    ],
                    intent="Wrap up with concrete implementation next steps",
                ),
            ],
        )

    def _generate_fake_slide_ir(self, user_prompt: str) -> SlideIR:
        prompt_lower = user_prompt.lower()
        if "cover" in prompt_lower or '"cover"' in prompt_lower:
            return SlideIR(
                schema_version=1,
                slide_key="s1",
                layout="cover",
                title="Scalable Architecture Blueprint",
                subtitle="Modern Event-Driven Microservices",
                blocks=[],
            )
        elif "closing" in prompt_lower or '"closing"' in prompt_lower:
            return SlideIR(
                schema_version=1,
                slide_key="s4",
                layout="closing",
                title="Execution Roadmap & Next Milestones",
                subtitle="Summary & Next Steps",
                blocks=[
                    TextBlock(
                        type="text",
                        style="bullets",
                        items=[
                            "Deploy managed Event Bus broker in Q1",
                            "Migrate high-volume ingress routes in Q2",
                            "Automate autoscaling policies across workers",
                        ],
                    )
                ],
            )
        elif "diagram" in prompt_lower or "flow" in prompt_lower or '"diagram"' in prompt_lower:
            # Check diagram kind
            kind = "flow"
            if "hierarchy" in prompt_lower:
                kind = "hierarchy"
            elif "layers" in prompt_lower:
                kind = "layers"
            elif "cycle" in prompt_lower:
                kind = "cycle"
            elif "timeline" in prompt_lower:
                kind = "timeline"
            elif "comparison" in prompt_lower:
                kind = "comparison"
            elif "mindmap" in prompt_lower:
                kind = "mindmap"

            if kind == "flow":
                return SlideIR(
                    schema_version=1,
                    slide_key="s3",
                    layout="diagram",
                    title="End-to-End Ingestion Flow Pipeline",
                    blocks=[
                        DiagramBlock(
                            type="diagram",
                            kind="flow",
                            direction="LR",
                            nodes=[
                                Node(
                                    id="client", label="Client App", shape="rect", emphasis="normal"
                                ),
                                Node(
                                    id="api_gw",
                                    label="API Gateway",
                                    shape="rounded",
                                    emphasis="primary",
                                ),
                                Node(
                                    id="event_bus",
                                    label="Event Bus",
                                    shape="rounded",
                                    emphasis="accent",
                                ),
                                Node(
                                    id="worker",
                                    label="Worker Node",
                                    shape="rect",
                                    emphasis="positive",
                                ),
                            ],
                            edges=[
                                Edge(source="client", target="api_gw", label="HTTP POST"),
                                Edge(source="api_gw", target="event_bus", label="Publish"),
                                Edge(source="event_bus", target="worker", label="Consume"),
                            ],
                        )
                    ],
                )
            elif kind == "cycle":
                return SlideIR(
                    schema_version=1,
                    slide_key="s3",
                    layout="diagram",
                    title="Continuous Improvement Cycle",
                    blocks=[
                        DiagramBlock(
                            type="diagram",
                            kind="cycle",
                            nodes=[
                                Node(
                                    id="plan_step",
                                    label="Plan",
                                    shape="rounded",
                                    emphasis="primary",
                                ),
                                Node(
                                    id="build_step",
                                    label="Build",
                                    shape="rounded",
                                    emphasis="normal",
                                ),
                                Node(
                                    id="measure_step",
                                    label="Measure",
                                    shape="rounded",
                                    emphasis="accent",
                                ),
                                Node(
                                    id="learn_step",
                                    label="Learn",
                                    shape="rounded",
                                    emphasis="positive",
                                ),
                            ],
                            edges=[],
                        )
                    ],
                )
            else:
                return SlideIR(
                    schema_version=1,
                    slide_key="s3",
                    layout="diagram",
                    title="System Component Architecture",
                    blocks=[
                        DiagramBlock(
                            type="diagram",
                            kind="flow",
                            direction="TB",
                            nodes=[
                                Node(
                                    id="root_node",
                                    label="System Core",
                                    shape="rect",
                                    emphasis="primary",
                                ),
                                Node(
                                    id="sub_a",
                                    label="Ingest Service",
                                    shape="rounded",
                                    emphasis="normal",
                                ),
                                Node(
                                    id="sub_b",
                                    label="Export Service",
                                    shape="rounded",
                                    emphasis="normal",
                                ),
                            ],
                            edges=[
                                Edge(source="root_node", target="sub_a"),
                                Edge(source="root_node", target="sub_b"),
                            ],
                        )
                    ],
                )
        else:
            return SlideIR(
                schema_version=1,
                slide_key="s2",
                layout="text",
                title="Current System Architecture Bottlenecks",
                blocks=[
                    TextBlock(
                        type="text",
                        style="bullets",
                        items=[
                            "Monolithic coupling increases deployment latency",
                            "Database connection exhaustion under traffic spikes",
                            "Lack of distributed tracing limits observability",
                        ],
                    )
                ],
            )


def get_llm_client() -> LLMClient:
    """Return FakeLLM if configured or LiteLLMClient for real calls."""
    if bool(settings.FAKE_LLM):
        return FakeLLM()
    return LiteLLMClient()
