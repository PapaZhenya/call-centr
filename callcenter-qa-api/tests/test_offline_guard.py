import pytest

from app.config import settings
from app.security.offline_guard import OfflineModeViolation, assert_local_url, is_local_host


def test_is_local_host_localhost_variants():
    assert is_local_host("localhost") is True
    assert is_local_host("127.0.0.1") is True
    assert is_local_host("0.0.0.0") is True


def test_is_local_host_bare_docker_service_name():
    assert is_local_host("ollama") is True
    assert is_local_host("db") is True


def test_is_local_host_rejects_public_domain():
    assert is_local_host("api.anthropic.com") is False
    assert is_local_host("api.openai.com") is False


@pytest.fixture
def offline_mode_enabled():
    original = settings.offline_mode
    settings.offline_mode = True
    yield
    settings.offline_mode = original


@pytest.fixture
def offline_mode_disabled():
    original = settings.offline_mode
    settings.offline_mode = False
    yield
    settings.offline_mode = original


def test_assert_local_url_allows_local_when_enabled(offline_mode_enabled):
    assert_local_url("http://localhost:11434")  # must not raise
    assert_local_url("http://ollama:11434")  # must not raise


def test_assert_local_url_blocks_external_when_enabled(offline_mode_enabled):
    with pytest.raises(OfflineModeViolation):
        assert_local_url("https://api.anthropic.com/v1/messages")


def test_assert_local_url_allows_anything_when_disabled(offline_mode_disabled):
    assert_local_url("https://api.anthropic.com/v1/messages")  # must not raise
