from pathlib import Path

from app.config import settings
from app.transcription.base import TranscriptSegment
from app.transcription.diarization import DiarizationTurn, SherpaDiarizer, assign_speakers


def seg(start: float, end: float, text: str = "x") -> TranscriptSegment:
    return TranscriptSegment(speaker=None, start=start, end=end, text=text)


def test_assign_speakers_picks_max_overlap():
    segments = [seg(0.0, 2.0), seg(2.0, 5.0)]
    turns = [
        DiarizationTurn(speaker="speaker_1", start=0.0, end=2.2),
        DiarizationTurn(speaker="speaker_2", start=2.2, end=5.0),
    ]

    assign_speakers(segments, turns)

    assert segments[0].speaker == "speaker_1"
    # 0.2s overlap with speaker_1 vs 2.8s with speaker_2
    assert segments[1].speaker == "speaker_2"


def test_assign_speakers_leaves_non_overlapping_segment_unlabeled():
    segments = [seg(10.0, 12.0)]
    turns = [DiarizationTurn(speaker="speaker_1", start=0.0, end=5.0)]

    assign_speakers(segments, turns)

    assert segments[0].speaker is None


def test_assign_speakers_with_no_turns_is_a_noop():
    segments = [seg(0.0, 1.0)]

    assign_speakers(segments, [])

    assert segments[0].speaker is None


def test_assign_speakers_segment_spanning_turns_takes_dominant_turn():
    # One whisper segment covering an exchange: 1s of speaker_1, 3s of speaker_2.
    segments = [seg(0.0, 4.0)]
    turns = [
        DiarizationTurn(speaker="speaker_1", start=0.0, end=1.0),
        DiarizationTurn(speaker="speaker_2", start=1.0, end=4.0),
    ]

    assign_speakers(segments, turns)

    assert segments[0].speaker == "speaker_2"


def test_try_diarize_returns_empty_when_models_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "diarization_models_dir", str(tmp_path / "nope"))
    diarizer = SherpaDiarizer()

    assert diarizer.is_available() is False
    assert diarizer.try_diarize(Path("whatever.wav")) == []


def test_try_diarize_respects_disabled_flag(tmp_path, monkeypatch):
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    (models_dir / "segmentation.onnx").write_bytes(b"stub")
    (models_dir / "embedding.onnx").write_bytes(b"stub")
    monkeypatch.setattr(settings, "diarization_models_dir", str(models_dir))
    monkeypatch.setattr(settings, "diarization_enabled", False)

    assert SherpaDiarizer().is_available() is False


def test_try_diarize_swallows_diarizer_errors(tmp_path, monkeypatch):
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    # Stub files pass is_available, but sherpa will reject them as models.
    (models_dir / "segmentation.onnx").write_bytes(b"stub")
    (models_dir / "embedding.onnx").write_bytes(b"stub")
    monkeypatch.setattr(settings, "diarization_models_dir", str(models_dir))

    diarizer = SherpaDiarizer()
    assert diarizer.is_available() is True
    assert diarizer.try_diarize(Path("whatever.wav")) == []
