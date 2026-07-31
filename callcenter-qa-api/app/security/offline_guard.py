"""Offline-mode network guard.

When OFFLINE_MODE=true (the default), the application must never make an
HTTP request to anything other than the local machine or another service in
the same Docker Compose network. This is the one guard that matters in this
codebase: since the Anthropic/Claude integration was removed, the local LLM
client (app/llm/ollama_provider.py) is the *only* outbound HTTP call site
the app's AI pipeline makes. Call `assert_local_url()` there before every
request.

This is a targeted allowlist check on the app's own HTTP client calls, not
an OS-level firewall - it guarantees no *code path in this application* can
silently start talking to a cloud AI API, which is the actual requirement.
"""

import logging
from urllib.parse import urlsplit

from app.config import settings

logger = logging.getLogger(__name__)

_ALLOWED_HOSTS = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "::1",
    # Docker's alias for the host machine - how a container reaches an
    # Ollama instance running natively on the host (the default setup).
    "host.docker.internal",
    "gateway.docker.internal",
}


class OfflineModeViolation(RuntimeError):
    """Raised when OFFLINE_MODE=true and the app attempted to reach a
    non-local host."""


def is_local_host(host: str) -> bool:
    host = host.lower()
    if host in _ALLOWED_HOSTS:
        return True
    # Bare hostnames with no dot are Docker Compose service names
    # (e.g. "ollama", "db", "redis") - never a public internet host.
    return "." not in host


def assert_local_url(url: str) -> None:
    if not settings.offline_mode:
        return

    host = urlsplit(url).hostname or ""
    if not is_local_host(host):
        logger.error("OFFLINE_MODE blocked an outbound request to non-local host: %s", host)
        raise OfflineModeViolation(
            f"OFFLINE_MODE is enabled - refusing to contact external host {host!r}. "
            "Set OFFLINE_MODE=false only if you understand the privacy implications."
        )
