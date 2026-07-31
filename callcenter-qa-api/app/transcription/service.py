from functools import lru_cache

from app.transcription.base import TranscriptionEngine
from app.transcription.faster_whisper_engine import FasterWhisperEngine


@lru_cache
def get_transcription_engine() -> TranscriptionEngine:
    # Only one engine for MVP; a TRANSCRIPTION_ENGINE config switch can select
    # a hosted alternative later without changing callers of this function.
    return FasterWhisperEngine()
