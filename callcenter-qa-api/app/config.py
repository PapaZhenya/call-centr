from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://callcenter:callcenter@localhost:5432/callcenter_qa"
    redis_url: str = "redis://localhost:6379/0"

    audio_storage_path: str = "./data/audio"

    # faster-whisper: model | device | compute_type. "auto" for device/compute_type
    # is resolved at model-load time based on local GPU availability - see
    # app/transcription/faster_whisper_engine.py:resolve_device_and_compute_type.
    whisper_model: str = "small"
    whisper_device: str = "auto"
    whisper_compute_type: str = "auto"

    # Local-only LLM for QA evaluation. No cloud AI provider is supported -
    # see app/llm/factory.py. "ollama" is the only implemented provider.
    local_llm_provider: str = "ollama"
    local_llm_base_url: str = "http://localhost:11434"
    local_llm_model: str = "qwen2.5:7b"
    local_llm_timeout: float = 300.0
    local_llm_temperature: float = 0.0
    local_llm_max_tokens: int = 4096
    local_llm_max_retries: int = 2

    # When true (default), the app refuses to make HTTP requests to any host
    # that isn't localhost/127.0.0.1 or a bare Docker Compose service name -
    # see app/security/offline_guard.py. This is the guarantee that no audio,
    # transcript, prompt, or evaluation result ever leaves the machine.
    offline_mode: bool = True

    # Auth
    jwt_secret_key: str = "change-me-in-.env-this-default-is-not-secure"
    jwt_access_token_ttl_minutes: int = 15
    jwt_refresh_token_ttl_days: int = 30
    login_max_failed_attempts: int = 5
    login_lockout_minutes: int = 15

    # Comma-separated list of origins allowed to call the API (the frontend's URL).
    cors_allowed_origins: str = "http://localhost:3000"

    @property
    def cors_allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


settings = Settings()
