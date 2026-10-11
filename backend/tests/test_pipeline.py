import pytest

from app.errors import GenerationError
from app.ir.schemas import DiagramBlock, Edge, Node, Plan, PlanSlide, SlideIR
from app.llm.client import FakeLLM
from app.llm.pipeline.plan import generate_plan
from app.llm.pipeline.slide import generate_slide
from app.models.deck import Deck


class PipelineMockLLM:
    """Mock LLM to test repair rounds and failure cases during slide generation."""

    def __init__(self, outputs: list[SlideIR]):
        self.outputs = outputs
        self.call_idx = 0

    async def structured_call(self, *args, **kwargs):
        if self.call_idx < len(self.outputs):
            res = self.outputs[self.call_idx]
            self.call_idx += 1
            return res
        raise RuntimeError("No more outputs configured")


@pytest.mark.asyncio
async def test_plan_post_processing_rules():
    deck = Deck(
        title="Pipeline Test Deck",
        settings={"slide_count": 4, "tone": "technical", "diagram_intensity": "high"},
    )
    fake_client = FakeLLM()

    # Pass dummy resources and image with specific IDs
    class MockRes:
        id = "11111111-1111-1111-1111-111111111111"
        filename = "arch.md"
        text = "Notes on distributed systems."

    class MockImg:
        asset_id = "real_asset_sha1"
        caption = "Figure 1"
        kind = "diagram"
        locator = "page 1"

    plan = await generate_plan(
        deck=deck,
        resources=[MockRes()],
        images=[MockImg()],
        client=fake_client,
    )

    # Verify keys are stable s1..sN
    assert [s.key for s in plan.slides] == [f"s{i}" for i in range(1, len(plan.slides) + 1)]

    # Verify image_ids filter: only real_asset_sha1 would be retained
    for s in plan.slides:
        assert all(aid == "real_asset_sha1" for aid in s.image_ids)


@pytest.mark.asyncio
async def test_slide_generation_happy_path():
    deck = Deck(title="System Overview", settings={"density": "standard"})
    fake_client = FakeLLM()

    plan_slide = PlanSlide(
        key="s1",
        role="cover",
        title="Scalable Architecture Blueprint",
        kind="text",
        intent="Introduce blueprint",
    )
    plan = Plan(
        title="System Overview",
        audience="Devs",
        goal="Explain architecture",
        narrative_summary="Summary",
        slides=[plan_slide],
    )

    ir, compile_result = await generate_slide(
        deck=deck,
        plan=plan,
        plan_slide=plan_slide,
        client=fake_client,
    )

    assert ir.layout == "cover"
    assert compile_result.skeleton is not None
    assert len(compile_result.errors) == 0


@pytest.mark.asyncio
async def test_slide_compile_error_repair_round():
    """Verify that a compilation error on turn 1 triggers a second turn that can recover."""
    deck = Deck(title="System Overview", settings={"density": "standard"})

    # Output 1 has a self-loop edge (compilation error)
    bad_ir = SlideIR(
        schema_version=1,
        slide_key="s2",
        layout="diagram",
        title="Component Graph",
        blocks=[
            DiagramBlock(
                type="diagram",
                kind="flow",
                nodes=[
                    Node(id="n1", label="Gateway"),
                    Node(id="n2", label="Backend"),
                ],
                edges=[Edge(source="n1", target="n1")],  # Self loop!
            )
        ],
    )

    # Output 2 fixes the self loop
    good_ir = SlideIR(
        schema_version=1,
        slide_key="s2",
        layout="diagram",
        title="Component Graph",
        blocks=[
            DiagramBlock(
                type="diagram",
                kind="flow",
                nodes=[
                    Node(id="n1", label="Gateway"),
                    Node(id="n2", label="Backend"),
                ],
                edges=[Edge(source="n1", target="n2")],  # Fixed!
            )
        ],
    )

    mock_llm = PipelineMockLLM([bad_ir, good_ir])

    plan_slide = PlanSlide(
        key="s2",
        role="process",
        title="Component Graph",
        kind="diagram",
        intent="Show connections",
    )
    plan = Plan(
        title="System Overview",
        audience="Devs",
        goal="Goal",
        narrative_summary="Summary",
        slides=[plan_slide],
    )

    ir, compile_result = await generate_slide(
        deck=deck,
        plan=plan,
        plan_slide=plan_slide,
        client=mock_llm,
    )

    assert mock_llm.call_idx == 2
    assert len(compile_result.errors) == 0
    assert compile_result.skeleton is not None


@pytest.mark.asyncio
async def test_slide_persistent_failure_raises_generation_error():
    """Verify that when both rounds fail compilation, GenerationError is raised."""
    deck = Deck(title="System Overview", settings={"density": "standard"})

    bad_ir = SlideIR(
        schema_version=1,
        slide_key="s2",
        layout="diagram",
        title="Broken Slide",
        blocks=[
            DiagramBlock(
                type="diagram",
                kind="flow",
                nodes=[Node(id="n1", label="Gateway")],
                edges=[Edge(source="n1", target="n1")],
            )
        ],
    )

    mock_llm = PipelineMockLLM([bad_ir, bad_ir])

    plan_slide = PlanSlide(
        key="s2",
        role="process",
        title="Broken Slide",
        kind="diagram",
        intent="Show broken",
    )
    plan = Plan(
        title="System Overview",
        audience="Devs",
        goal="Goal",
        narrative_summary="Summary",
        slides=[plan_slide],
    )

    with pytest.raises(GenerationError) as exc_info:
        await generate_slide(
            deck=deck,
            plan=plan,
            plan_slide=plan_slide,
            client=mock_llm,
        )

    assert "Slide compilation failed" in str(exc_info.value)
    assert len(exc_info.value.issues) > 0
