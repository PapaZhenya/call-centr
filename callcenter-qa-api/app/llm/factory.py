from functools import lru_cache

from app.config import settings
from app.llm.base import LocalLLMProvider
from app.llm.ollama_provider import OllamaProvider


@lru_cache
def get_llm_provider() -> LocalLLMProvider:
    provider = settings.local_llm_provider.lower()
    if provider == "ollama":
        return OllamaProvider()
    # llama.cpp / vLLM are documented future seams (LocalLLMProvider), not
    # implemented yet - fail loudly rather than silently falling back.
    raise NotImplementedError(
        f"LOCAL_LLM_PROVIDER={provider!r} is not implemented. Only 'ollama' is "
        "currently supported."
    )
