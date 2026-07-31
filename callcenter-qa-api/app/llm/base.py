from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResult:
    parsed: dict
    raw_text: str
    raw_response: dict


class LLMOutputInvalidError(RuntimeError):
    """Raised when the local model failed to produce schema-valid JSON after
    all configured retries. Carries the last raw response for diagnostics -
    callers should persist it (see QAEvaluation.raw_llm_response) rather than
    discard it."""

    def __init__(self, message: str, raw_text: str):
        super().__init__(message)
        self.raw_text = raw_text


class LocalLLMProvider(ABC):
    """Seam for local-only LLM backends. `OllamaProvider` is the only
    implementation for now; llama.cpp/vLLM providers can be added later
    (selected via LOCAL_LLM_PROVIDER, see app/llm/factory.py) without
    changing any caller of this interface."""

    @abstractmethod
    async def generate_json(
        self, system_prompt: str, user_prompt: str, json_schema: dict
    ) -> LLMResult: ...
