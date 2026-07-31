import json
import logging

import httpx

from app.config import settings
from app.llm.base import LLMOutputInvalidError, LLMResult, LocalLLMProvider
from app.security.offline_guard import assert_local_url

logger = logging.getLogger(__name__)

_RETRY_INSTRUCTION = (
    "\n\nYour previous response was not valid JSON matching the required schema. "
    "Respond with ONLY a single valid JSON object - no prose, no markdown code fences, "
    "no explanation before or after it."
)


class OllamaProvider(LocalLLMProvider):
    """Calls a locally running Ollama server (https://ollama.com) over its
    HTTP API (`POST /api/generate`). Runs entirely on the user's machine -
    see app/security/offline_guard.py for the enforcement that this never
    targets a non-local host."""

    def __init__(self) -> None:
        self._base_url = settings.local_llm_base_url.rstrip("/")

    async def generate_json(
        self, system_prompt: str, user_prompt: str, json_schema: dict
    ) -> LLMResult:
        assert_local_url(self._base_url)

        schema_instruction = (
            "\n\nYour entire response must be a single JSON object matching exactly this "
            f"JSON Schema (no extra keys, all required keys present):\n{json.dumps(json_schema)}"
        )
        prompt = user_prompt + schema_instruction
        last_raw_text = ""
        max_attempts = settings.local_llm_max_retries + 1

        async with httpx.AsyncClient(timeout=settings.local_llm_timeout) as client:
            for attempt in range(1, max_attempts + 1):
                response = await client.post(
                    f"{self._base_url}/api/generate",
                    json={
                        "model": settings.local_llm_model,
                        "system": system_prompt,
                        "prompt": prompt,
                        "format": "json",
                        "stream": False,
                        "options": {
                            "temperature": settings.local_llm_temperature,
                            "num_predict": settings.local_llm_max_tokens,
                        },
                    },
                )
                response.raise_for_status()
                payload = response.json()
                raw_text = payload.get("response", "")
                last_raw_text = raw_text

                try:
                    parsed = json.loads(raw_text)
                except json.JSONDecodeError:
                    logger.warning(
                        "Local LLM returned invalid JSON (attempt %s/%s)", attempt, max_attempts
                    )
                    prompt = user_prompt + schema_instruction + _RETRY_INSTRUCTION
                    continue

                return LLMResult(parsed=parsed, raw_text=raw_text, raw_response=payload)

        raise LLMOutputInvalidError(
            f"Local LLM did not return valid JSON after {max_attempts} attempt(s)",
            raw_text=last_raw_text,
        )
