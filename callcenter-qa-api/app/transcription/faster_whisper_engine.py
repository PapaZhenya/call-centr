import asyncio
import logging
import wave
from array import array
from pathlib import Path

import ctranslate2
from faster_whisper import WhisperModel

from app.config import settings
from app.transcription.base import TranscriptionEngine, TranscriptionResult, TranscriptSegment

logger = logging.getLogger(__name__)


def resolve_device_and_compute_type(device_setting: str, compute_type_setting: str) -> tuple[str, str]:
    """Resolves WHISPER_DEVICE=auto / WHISPER_COMPUTE_TYPE=auto against the
    hardware actually available on this machine, so the same .env works
    unchanged on a GPU box or a CPU-only laptop."""
    device = device_setting
    if device == "auto":
        try:
            device = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
        except Exception:
            logger.warning("GPU detection failed - falling back to CPU", exc_info=True)
            device = "cpu"

    compute_type = compute_type_setting
    if compute_type == "auto":
        compute_type = "float16" if device == "cuda" else "int8"

    return device, compute_type


class FasterWhisperEngine(TranscriptionEngine):
    """Local ASR via faster-whisper. Stereo WAV recordings (the common case for
    call center audio: agent/customer on separate channels) are transcribed
    per-channel and labeled by channel. Anything else (mono, or non-16-bit PCM,
    or non-WAV) is transcribed as a single stream with no speaker labels -
    a documented MVP limitation; real diarization is a future seam
    (pyannote.audio)."""

    def __init__(self) -> None:
        self._model: WhisperModel | None = None

    def _get_model(self) -> WhisperModel:
        if self._model is None:
            device, compute_type = resolve_device_and_compute_type(
                settings.whisper_device, settings.whisper_compute_type
            )
            logger.info(
                "Loading faster-whisper model=%s device=%s compute_type=%s",
                settings.whisper_model,
                device,
                compute_type,
            )
            self._model = WhisperModel(
                settings.whisper_model,
                device=device,
                compute_type=compute_type,
            )
        return self._model

    async def transcribe(self, audio_path: Path) -> TranscriptionResult:
        return await asyncio.to_thread(self._transcribe_sync, audio_path)

    def _transcribe_sync(self, audio_path: Path) -> TranscriptionResult:
        channel_paths = self._try_split_stereo_channels(audio_path)

        if channel_paths is not None:
            model = self._get_model()
            segments: list[TranscriptSegment] = []
            language: str | None = None
            try:
                for channel_path, speaker in channel_paths:
                    raw_segments, info = model.transcribe(str(channel_path))
                    language = language or info.language
                    for seg in raw_segments:
                        segments.append(
                            TranscriptSegment(
                                speaker=speaker, start=seg.start, end=seg.end, text=seg.text.strip()
                            )
                        )
            finally:
                for channel_path, _ in channel_paths:
                    channel_path.unlink(missing_ok=True)
            segments.sort(key=lambda s: s.start)
        else:
            model = self._get_model()
            raw_segments, info = model.transcribe(str(audio_path))
            language = info.language
            segments = [
                TranscriptSegment(speaker=None, start=seg.start, end=seg.end, text=seg.text.strip())
                for seg in raw_segments
            ]

        full_text = " ".join(s.text for s in segments).strip()
        return TranscriptionResult(
            full_text=full_text,
            segments=segments,
            language=language,
            engine="faster_whisper",
            engine_model=settings.whisper_model,
        )

    def _try_split_stereo_channels(
        self, audio_path: Path
    ) -> list[tuple[Path, str]] | None:
        """Returns [(channel_path, speaker_label), ...] for a 2-channel, 16-bit
        PCM WAV file, or None if the file doesn't match that shape (caller
        should fall back to whole-file mono transcription)."""
        try:
            with wave.open(str(audio_path), "rb") as wf:
                n_channels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                framerate = wf.getframerate()
                n_frames = wf.getnframes()
                raw = wf.readframes(n_frames)
        except (wave.Error, EOFError, FileNotFoundError):
            return None  # not a readable WAV (e.g. mp3/m4a) - whole-file fallback

        if n_channels != 2 or sampwidth != 2:
            return None

        samples = array("h")
        samples.frombytes(raw)

        paths = []
        for channel_index, speaker in ((0, "agent"), (1, "customer")):
            channel_samples = samples[channel_index::2]
            out_path = audio_path.with_name(f"{audio_path.stem}_ch{channel_index}.wav")
            with wave.open(str(out_path), "wb") as out:
                out.setnchannels(1)
                out.setsampwidth(2)
                out.setframerate(framerate)
                out.writeframes(channel_samples.tobytes())
            paths.append((out_path, speaker))
        return paths
