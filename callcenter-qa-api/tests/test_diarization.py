from pathlib import Path

from app.config import settings
from app.transcription.base import TranscriptSegment
from app.transcription.diarization import (
    DiarizationTurn,
    SherpaDiarizer,
    assign_speakers,
    map_speakers_to_roles,
)


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


def _labeled(speaker: str, start: float, end: float) -> TranscriptSegment:
    return TranscriptSegment(speaker=speaker, start=start, end=end, text="x")


def test_map_speakers_inbound_first_speaker_is_agent():
    segments = [_labeled("speaker_1", 0.0, 2.0), _labeled("speaker_2", 2.0, 4.0)]

    map_speakers_to_roles(segments, "inbound")

    assert segments[0].speaker == "agent"
    assert segments[1].speaker == "customer"


def test_map_speakers_outbound_first_speaker_is_customer():
    # First voice on an outbound call is the customer picking up.
    segments = [_labeled("speaker_2", 0.5, 2.0), _labeled("speaker_1", 2.0, 4.0)]

    map_speakers_to_roles(segments, "outbound")

    assert segments[0].speaker == "customer"
    assert segments[1].speaker == "agent"


def test_map_speakers_unknown_direction_keeps_neutral_labels():
    segments = [_labeled("speaker_1", 0.0, 2.0), _labeled("speaker_2", 2.0, 4.0)]

    map_speakers_to_roles(segments, None)

    assert segments[0].speaker == "speaker_1"
    assert segments[1].speaker == "speaker_2"


def test_map_speakers_single_voice_left_untouched():
    segments = [_labeled("speaker_1", 0.0, 2.0), _labeled("speaker_1", 2.0, 4.0)]

    map_speakers_to_roles(segments, "inbound")

    assert all(s.speaker == "speaker_1" for s in segments)


def test_map_speakers_channel_labeled_stereo_left_untouched():
    # Stereo split already produced agent/customer - mapping must not touch it.
    segments = [_labeled("agent", 0.0, 2.0), _labeled("customer", 2.0, 4.0)]

    map_speakers_to_roles(segments, "inbound")

    assert segments[0].speaker == "agent"
    assert segments[1].speaker == "customer"


def test_map_speakers_unlabeled_segment_stays_unlabeled():
    segments = [
        _labeled("speaker_1", 0.0, 2.0),
        TranscriptSegment(speaker=None, start=2.0, end=3.0, text="x"),
        _labeled("speaker_2", 3.0, 4.0),
    ]

    map_speakers_to_roles(segments, "inbound")

    assert segments[0].speaker == "agent"
    assert segments[1].speaker is None
    assert segments[2].speaker == "customer"


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
