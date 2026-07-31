import struct
import wave

from app.transcription.faster_whisper_engine import FasterWhisperEngine


def _write_stereo_wav(path, framerate=8000, n_frames=1600):
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(framerate)
        frames = b"".join(struct.pack("<hh", i % 100, -(i % 100)) for i in range(n_frames))
        wf.writeframes(frames)


def _write_mono_wav(path, framerate=8000, n_frames=1600):
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(framerate)
        wf.writeframes(struct.pack("<h", 0) * n_frames)


def test_split_stereo_channels(tmp_path):
    wav_path = tmp_path / "stereo.wav"
    _write_stereo_wav(wav_path)

    engine = FasterWhisperEngine()
    result = engine._try_split_stereo_channels(wav_path)

    assert result is not None
    assert [speaker for _, speaker in result] == ["agent", "customer"]
    for channel_path, _ in result:
        with wave.open(str(channel_path), "rb") as wf:
            assert wf.getnchannels() == 1
            assert wf.getnframes() == 1600
        channel_path.unlink()


def test_mono_wav_returns_none(tmp_path):
    wav_path = tmp_path / "mono.wav"
    _write_mono_wav(wav_path)

    engine = FasterWhisperEngine()
    assert engine._try_split_stereo_channels(wav_path) is None


def test_non_wav_file_returns_none(tmp_path):
    fake_path = tmp_path / "call.mp3"
    fake_path.write_bytes(b"not a real mp3")

    engine = FasterWhisperEngine()
    assert engine._try_split_stereo_channels(fake_path) is None
