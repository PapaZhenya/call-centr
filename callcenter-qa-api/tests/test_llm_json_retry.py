import json

import httpx
import pytest

from app.config import settings
from app.llm.base import LLMOutputInvalidError
from app.llm.ollama_provider import OllamaProvider
from app.security.offline_guard import OfflineModeViolation


def _mock_ollama(monkeypatch, responses: list[str]) -> list[dict]:
    """Patches httpx.AsyncClient so every POST returns the next entry in
    `responses` as Ollama's raw `response` field, in order. Returns the list
    of decoded request bodies so tests can assert on what was actually sent
    (e.g. the corrective retry instruction)."""
    calls: list[dict] = []
    responses_iter = iter(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        calls.append(body)
        return httpx.Response(
            200, json={"model": body["model"], "response": next(responses_iter), "done": True}
        )

    original_init = httpx.AsyncClient.__init__

    def patched_init(self, *args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        original_init(self, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", patched_init)
    return calls


@pytest.mark.asyncio
async def test_generate_json_succeeds_first_try(monkeypatch):
    calls = _mock_ollama(monkeypatch, [json.dumps({"overall_score": 5})])

    provider = OllamaProvider()
    result = await provider.generate_json("system", "user", {"type": "object"})

    assert result.parsed == {"overall_score": 5}
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_generate_json_retries_on_invalid_json_then_succeeds(monkeypatch):
    calls = _mock_ollama(monkeypatch, ["not valid json", json.dumps({"overall_score": 3})])

    provider = OllamaProvider()
    result = await provider.generate_json("system", "user", {"type": "object"})

    assert result.parsed == {"overall_score": 3}
    assert len(calls) == 2
    assert "valid JSON" in calls[1]["prompt"]  # corrective instruction on retry


@pytest.mark.asyncio
async def test_generate_json_raises_after_exhausting_retries(monkeypatch):
    calls = _mock_ollama(monkeypatch, ["nope", "still nope", "nope again"])

    provider = OllamaProvider()
    with pytest.raises(LLMOutputInvalidError) as exc_info:
        await provider.generate_json("system", "user", {"type": "object"})

    assert len(calls) == 1 + settings.local_llm_max_retries
    assert exc_info.value.raw_text  # raw text preserved for diagnostics


@pytest.mark.asyncio
async def test_generate_json_blocked_when_base_url_is_external(monkeypatch):
    monkeypatch.setattr(settings, "local_llm_base_url", "https://api.anthropic.com")
    monkeypatch.setattr(settings, "offline_mode", True)

    provider = OllamaProvider()
    with pytest.raises(OfflineModeViolation):
        await provider.generate_json("system", "user", {"type": "object"})
