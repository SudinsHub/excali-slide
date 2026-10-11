from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel, Field

from app.ir.schemas import Plan, SlideIR
from app.llm.client import FakeLLM, LiteLLMClient


class DemoSchema(BaseModel):
    title: str = Field(..., max_length=50)
    score: int


def _mock_choice(content: str):
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    resp.usage = MagicMock(prompt_tokens=10, completion_tokens=20)
    return resp


@pytest.mark.asyncio
async def test_structured_call_valid_output():
    client = LiteLLMClient()
    mock_resp = _mock_choice('{"title": "Valid Run", "score": 42}')

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acomp:
        mock_acomp.return_value = mock_resp
        result = await client.structured_call(
            model="mock/model",
            system="System instructions",
            user="User query",
            schema=DemoSchema,
        )

    assert result.title == "Valid Run"
    assert result.score == 42
    assert mock_acomp.call_count == 1


@pytest.mark.asyncio
async def test_structured_call_repair_turn_success():
    client = LiteLLMClient()
    # Turn 1: Invalid missing score, Turn 2: Fixed valid JSON
    turn1_resp = _mock_choice('{"title": "Broken Run"}')
    turn2_resp = _mock_choice('{"title": "Repaired Run", "score": 99}')

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acomp:
        mock_acomp.side_effect = [turn1_resp, turn2_resp]
        result = await client.structured_call(
            model="mock/model",
            system="System instructions",
            user="User query",
            schema=DemoSchema,
        )

    assert result.title == "Repaired Run"
    assert result.score == 99
    assert mock_acomp.call_count == 2


@pytest.mark.asyncio
async def test_structured_call_exhaustion_raises():
    client = LiteLLMClient()
    bad_resp = _mock_choice('{"invalid": "always"}')

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acomp:
        mock_acomp.side_effect = [bad_resp, bad_resp, bad_resp]
        with pytest.raises(Exception, match=r".+"):
            await client.structured_call(
                model="mock/model",
                system="System instructions",
                user="User query",
                schema=DemoSchema,
            )

    assert mock_acomp.call_count == 3


@pytest.mark.asyncio
async def test_structured_call_schema_fallback():
    client = LiteLLMClient()
    valid_resp = _mock_choice('{"title": "Fallback Success", "score": 100}')

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_acomp:
        # First call raises provider unsupported response_format error
        mock_acomp.side_effect = [
            ValueError("Provider does not support response_format with json_schema"),
            valid_resp,
        ]
        result = await client.structured_call(
            model="mock/model",
            system="System instructions",
            user="User query",
            schema=DemoSchema,
        )

    assert result.title == "Fallback Success"
    assert result.score == 100
    assert mock_acomp.call_count == 2


@pytest.mark.asyncio
async def test_fake_llm_behaviors():
    fake = FakeLLM()

    # Plan generation
    plan = await fake.structured_call(
        model="fake", system="sys", user="brief", schema=Plan, purpose="planner"
    )
    assert isinstance(plan, Plan)
    assert len(plan.slides) >= 3

    # SlideIR generation
    slide_ir = await fake.structured_call(
        model="fake", system="sys", user="diagram flow slide", schema=SlideIR, purpose="slide"
    )
    assert isinstance(slide_ir, SlideIR)
    assert slide_ir.layout == "diagram"

    # Injectable failure
    failing_fake = FakeLLM(inject_failure=RuntimeError("Injected test failure"))
    with pytest.raises(RuntimeError, match="Injected test failure"):
        await failing_fake.structured_call(model="fake", system="sys", user="u", schema=Plan)
