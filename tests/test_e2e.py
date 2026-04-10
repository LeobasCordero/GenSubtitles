"""
End-to-end tests for GenSubtitles.

Tests validate both CLI and API paths with synthetic test video:
- CLI without translation
- CLI with translation (English → Spanish)
- API without translation

All tests verify SRT timecode format and cleanup temp files.
"""
import re
import subprocess
import tempfile
import time
from pathlib import Path

import pytest
import requests


def validate_srt_timecodes(srt_content: str) -> bool:
    """Check SRT has valid timecode format."""
    pattern = r"\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}"
    return bool(re.search(pattern, srt_content))


@pytest.mark.slow
@pytest.mark.e2e
def test_cli_without_translation():
    """E2E: CLI generates SRT from synthetic video."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output = Path(tmpdir) / "output.srt"
        result = subprocess.run(
            [
                "python",
                "main.py",
                "--input",
                "tests/fixtures/e2e_test.mp4",
                "--output",
                str(output),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )

        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        assert output.exists(), "SRT not created"

        content = output.read_text(encoding="utf-8")
        assert validate_srt_timecodes(content), "No valid timecodes in SRT"
        assert len(content) > 10, "SRT too short"


@pytest.mark.slow
@pytest.mark.e2e
def test_cli_with_translation():
    """E2E: CLI generates Spanish SRT from English audio."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output = Path(tmpdir) / "output_es.srt"
        result = subprocess.run(
            [
                "python",
                "main.py",
                "--input",
                "tests/fixtures/e2e_test.mp4",
                "--output",
                str(output),
                "--target-lang",
                "es",
            ],
            capture_output=True,
            text=True,
            timeout=180,  # Translation takes longer
        )

        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        assert output.exists(), "Spanish SRT not created"

        content = output.read_text(encoding="utf-8")
        assert validate_srt_timecodes(content), "No valid timecodes in SRT"
        # Note: Can't reliably check for Spanish words without knowing TTS content


@pytest.mark.slow
@pytest.mark.e2e
def test_api_without_translation():
    """E2E: API endpoint generates SRT from video upload."""
    # Start server in background
    proc = subprocess.Popen(
        [
            "uvicorn",
            "gensubtitles.api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8888",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        # Wait for server startup
        time.sleep(3)

        # Upload video
        with open("tests/fixtures/e2e_test.mp4", "rb") as f:
            files = {"file": ("test.mp4", f, "video/mp4")}
            response = requests.post(
                "http://127.0.0.1:8888/subtitles", files=files, timeout=120
            )

        assert response.status_code == 200, f"API failed: {response.text}"
        assert response.headers["content-type"] == "text/plain; charset=utf-8"

        srt_content = response.text
        assert validate_srt_timecodes(srt_content), "No valid timecodes in SRT"
        assert len(srt_content) > 10, "SRT too short"

    finally:
        proc.terminate()
        proc.wait(timeout=5)
