"""
Shared pytest fixtures for GenSubtitles test suite.
"""
import subprocess
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def synthetic_video(tmp_path_factory) -> Path:
    """
    Session-scoped fixture: generate a 1-second synthetic mp4 with audio via FFmpeg.

    Uses FFmpeg lavfi (virtual device) — no binary input file required.
    Generated once per test session; reused by all audio tests.

    Video:  testsrc color-bar pattern, 320x240, 25fps, 1 second
    Audio:  440Hz sine wave, 1 second (non-silent — avoids VAD suppression in later phases)
    """
    tmp_dir = tmp_path_factory.mktemp("fixtures")
    output = tmp_dir / "test_video.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=25",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
            "-c:v", "libx264",
            "-c:a", "aac",
            "-shortest",
            str(output),
        ],
        capture_output=True,
        check=True,  # Raises subprocess.CalledProcessError if ffmpeg fails
    )
    return output


@pytest.fixture(scope="session")
def silent_video(tmp_path_factory) -> Path:
    """
    Session-scoped fixture: generate a 1-second synthetic mp4 with NO audio stream.

    Used to test AUD-03 (missing audio track raises AudioExtractionError).
    """
    tmp_dir = tmp_path_factory.mktemp("fixtures")
    output = tmp_dir / "silent_video.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=25",
            "-an",  # Explicitly remove audio stream
            "-c:v", "libx264",
            str(output),
        ],
        capture_output=True,
        check=True,
    )
    return output
