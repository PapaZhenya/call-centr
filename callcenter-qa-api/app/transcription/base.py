from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TranscriptSegment:
    speaker: str | None
    start: float
    end: float
    text: str


@dataclass
class TranscriptionResult:
    full_text: str
    segments: list[TranscriptSegment]
    language: str | None
    engine: str
    engine_model: str


class TranscriptionEngine(ABC):
    """ASR seam: FasterWhisperEngine is the MVP implementation. A hosted engine
    (Deepgram/AssemblyAI) can implement this same interface later, selected via
    config, with no changes to the pipeline that calls it."""

    @abstractmethod
    async def transcribe(self, audio_path: Path) -> TranscriptionResult: ...
