"""Speaker diarization for mono / non-WAV recordings via sherpa-onnx.

Stereo call recordings don't need this - they carry the agent/customer split
in their channels (see FasterWhisperEngine._try_split_stereo_channels). This
module covers everything else: a pyannote segmentation-3.0 ONNX model finds
speech turns, an ERes2Net embedding model + clustering groups them into
speakers, and `assign_speakers` maps whisper segments onto those turns by
temporal overlap.

Everything runs locally on CPU via onnxruntime - no cloud calls, no gated
model downloads, no HF account (models come from the sherpa-onnx GitHub
releases; see scripts/download-models.ps1). If the models aren't downloaded
or sherpa-onnx isn't importable, diarization silently degrades to unlabeled
segments - transcription itself must never fail because of it.
"""

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.config import settings
from app.transcription.base import TranscriptSegment

logger = logging.getLogger(__name__)

SEGMENTATION_MODEL_FILENAME = "segmentation.onnx"
EMBEDDING_MODEL_FILENAME = "embedding.onnx"


@dataclass
class DiarizationTurn:
    speaker: str  # "speaker_1", "speaker_2", ...
    start: float
    end: float


def assign_speakers(
    segments: list[TranscriptSegment], turns: list[DiarizationTurn]
) -> list[TranscriptSegment]:
    """Labels each transcript segment with the turn speaker it overlaps most,
    in place. A segment that overlaps no turn at all keeps speaker=None
    (silence padding, music, or diarization missing that region)."""
    for segment in segments:
        best_speaker: str | None = None
        best_overlap = 0.0
        for turn in turns:
            overlap = min(segment.end, turn.end) - max(segment.start, turn.start)
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = turn.speaker
        if best_speaker is not None:
            segment.speaker = best_speaker
    return segments


class SherpaDiarizer:
    """Lazy wrapper around sherpa_onnx.OfflineSpeakerDiarization. Model files
    are looked up in settings.diarization_models_dir under fixed names
    (download-models.ps1 puts them there)."""

    def __init__(self) -> None:
        self._sd = None

    def _models_dir(self) -> Path:
        return Path(settings.diarization_models_dir)

    def is_available(self) -> bool:
        return (
            settings.diarization_enabled
            and (self._models_dir() / SEGMENTATION_MODEL_FILENAME).is_file()
            and (self._models_dir() / EMBEDDING_MODEL_FILENAME).is_file()
        )

    def _get_diarizer(self):
        if self._sd is None:
            import sherpa_onnx  # deferred: heavy import, only when actually used

            config = sherpa_onnx.OfflineSpeakerDiarizationConfig(
                segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
                    pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(
                        model=str(self._models_dir() / SEGMENTATION_MODEL_FILENAME)
                    ),
                ),
                embedding=sherpa_onnx.SpeakerEmbeddingExtractorConfig(
                    model=str(self._models_dir() / EMBEDDING_MODEL_FILENAME)
                ),
                clustering=sherpa_onnx.FastClusteringConfig(
                    num_clusters=settings.diarization_num_speakers,
                    threshold=settings.diarization_cluster_threshold,
                ),
                min_duration_on=0.3,
                min_duration_off=0.5,
            )
            # Construction itself raises/aborts on unreadable model files;
            # try_diarize turns that into "segments stay unlabeled".
            self._sd = sherpa_onnx.OfflineSpeakerDiarization(config)
        return self._sd

    def _decode_audio(self, audio_path: Path, sample_rate: int):
        """Decodes any ffmpeg-readable file (wav/mp3/m4a/ogg/flac) to mono
        float32 PCM at the diarizer's expected sample rate."""
        import numpy as np

        proc = subprocess.run(
            [
                "ffmpeg",
                "-nostdin",
                "-i",
                str(audio_path),
                "-f",
                "f32le",
                "-ac",
                "1",
                "-ar",
                str(sample_rate),
                "pipe:1",
            ],
            capture_output=True,
            check=True,
        )
        return np.frombuffer(proc.stdout, dtype=np.float32)

    def diarize(self, audio_path: Path) -> list[DiarizationTurn]:
        sd = self._get_diarizer()
        audio = self._decode_audio(audio_path, sd.sample_rate)
        if len(audio) == 0:
            return []
        result = sd.process(audio).sort_by_start_time()
        return [
            DiarizationTurn(speaker=f"speaker_{r.speaker + 1}", start=r.start, end=r.end)
            for r in result
        ]

    def try_diarize(self, audio_path: Path) -> list[DiarizationTurn]:
        """Best-effort entry point used by the transcription engine: returns
        [] instead of raising, because a failed diarization must not fail the
        whole transcription job."""
        if not self.is_available():
            return []
        try:
            return self.diarize(audio_path)
        except Exception:
            logger.warning("Diarization failed for %s - segments stay unlabeled", audio_path, exc_info=True)
            return []
