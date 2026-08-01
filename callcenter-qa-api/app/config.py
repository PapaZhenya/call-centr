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

    # Speaker diarization for mono/non-WAV recordings (stereo calls are split
    # by channel instead - see FasterWhisperEngine). Runs locally via
    # sherpa-onnx; models are downloaded by scripts/download-models.ps1 into
    # DIARIZATION_MODELS_DIR. If the models are missing, transcription still
    # works - segments just stay unlabeled. num_speakers=2 fits call center
    # audio; set -1 to auto-detect (then cluster_threshold matters: lower =
    # more speakers).
    diarization_enabled: bool = True
    diarization_models_dir: str = "./data/diarization"
    diarization_num_speakers: int = 2
    diarization_cluster_threshold: float = 0.5

    # Local-only LLM for QA evaluation. No cloud AI provider is supported -
    # see app/llm/factory.py. "ollama" is the only implemented provider.
    local_llm_provider: str = "ollama"
    local_llm_base_url: str = "http://localhost:11434"
    local_llm_model: str = "qwen2.5:7b"
    local_llm_timeout: float = 300.0
    local_llm_temperature: float = 0.0
    local_llm_max_tokens: int = 4096
    local_llm_max_retries: int = 2

    # A transcript with fewer words than this is scored at the minimum for
    # every LLM criterion without calling the model at all (flag:
    # insufficient_transcript). Silence, hold music, or a dropped call can't
    # demonstrate quality - and shouldn't cost minutes of local LLM time.
    qa_min_transcript_words: int = 20

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
