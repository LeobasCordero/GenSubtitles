"""
Phase 2 audio extraction tests — covers AUD-01, AUD-02, AUD-03, AUD-04.
"""
import shutil
import wave
from pathlib import Path

import pytest

# Mark all tests in this module as skipped when FFmpeg is absent.
# The import-time EnvironmentError in audio.py (tested separately by INF-04)
# means we must guard the import too; tests are collected but skipped, so
# pytest exits 0 rather than 5 ("no tests collected").
pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None,
    reason="FFmpeg not installed — audio tests require a working FFmpeg binary",
)

try:
    from gensubtitles.core.audio import SUPPORTED_EXTENSIONS, audio_temp_context, extract_audio
    from gensubtitles.exceptions import AudioExtractionError
except EnvironmentError:
    # FFmpeg absent — symbols are undefined but tests will be skipped via pytestmark
    SUPPORTED_EXTENSIONS = frozenset()  # type: ignore[assignment]
    extract_audio = None  # type: ignore[assignment]
    audio_temp_context = None  # type: ignore[assignment]
    AudioExtractionError = Exception  # type: ignore[assignment,misc]


def test_extract_audio_creates_valid_wav(synthetic_video, tmp_path):
    """
    AUD-02: extract_audio produces a 16kHz mono WAV file.
    Uses synthetic_video fixture (real FFmpeg, no mocking).
    """
    output_wav = tmp_path / "output.wav"
    extract_audio(synthetic_video, output_wav)

    assert output_wav.exists(), "Output WAV file was not created"

    with wave.open(str(output_wav), "rb") as wf:
        assert wf.getframerate() == 16000, f"Expected 16000Hz, got {wf.getframerate()}"
        assert wf.getnchannels() == 1, f"Expected mono (1 channel), got {wf.getnchannels()}"
        assert wf.getnframes() > 0, "WAV file contains no audio frames"


def test_extract_audio_unsupported_extension(tmp_path):
    """
    AUD-01: extract_audio raises ValueError for unsupported file extensions,
    before spawning any FFmpeg subprocess.
    """
    fake_file = tmp_path / "video.xyz"
    fake_file.touch()  # File exists but extension is unsupported

    with pytest.raises(ValueError, match="xyz"):
        extract_audio(fake_file, tmp_path / "output.wav")


def test_extract_audio_missing_audio_track(silent_video, tmp_path):
    """
    AUD-03: extract_audio raises AudioExtractionError when the video has no audio stream.
    FFmpeg exits non-zero; full stderr is included in the error message.
    """
    output_wav = tmp_path / "output.wav"

    with pytest.raises(AudioExtractionError):
        extract_audio(silent_video, output_wav)


def test_audio_temp_context_cleanup_normal(synthetic_video):
    """
    AUD-04: audio_temp_context deletes the temp file after the context exits normally.
    """
    with audio_temp_context() as tmp_wav:
        assert isinstance(tmp_wav, Path), "Fixture should yield a pathlib.Path"
        extract_audio(synthetic_video, tmp_wav)
        assert tmp_wav.exists(), "Temp WAV should exist inside the context"

    assert not tmp_wav.exists(), "Temp WAV should be deleted after the context exits"


def test_audio_temp_context_cleanup_on_exception(synthetic_video):
    """
    AUD-04: audio_temp_context deletes the temp file even when an exception is raised
    inside the context block.
    """
    recorded_path: Path | None = None

    with pytest.raises(RuntimeError, match="intentional"):
        with audio_temp_context() as tmp_wav:
            recorded_path = tmp_wav
            extract_audio(synthetic_video, tmp_wav)
            raise RuntimeError("intentional test exception")

    assert recorded_path is not None
    assert not recorded_path.exists(), "Temp WAV must be deleted even after exception"
