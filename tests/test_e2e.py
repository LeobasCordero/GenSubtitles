"""
End-to-end tests for GenSubtitles.

Tests validate both CLI and API paths with synthetic test video:
- CLI without translation
- CLI with translation (English → Spanish)
- API without translation

All tests verify SRT timecode format and cleanup temp files.

These tests are opt-in and skipped by default. To run them:
    RUN_E2E_TESTS=1 pytest -m e2e
"""
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest
import requests

# ---------------------------------------------------------------------------
# Skip conditions
# ---------------------------------------------------------------------------

_e2e_enabled = os.environ.get("RUN_E2E_TESTS", "").strip() not in ("", "0")
_ffmpeg_available = shutil.which("ffmpeg") is not None

skip_no_e2e = pytest.mark.skipif(
    not _e2e_enabled,
    reason="Set RUN_E2E_TESTS=1 to enable E2E tests",
)
skip_no_ffmpeg = pytest.mark.skipif(
    not _ffmpeg_available,
    reason="ffmpeg not found on PATH",
)


def _argos_pair_installed(source: str, target: str) -> bool:
    """Return True if the Argos translation package for source→target is installed."""
    try:
        import argostranslate.package  # type: ignore

        installed = argostranslate.package.get_installed_packages()
        return any(
            p.from_code == source and p.to_code == target for p in installed
        )
    except Exception:
        return False


def _free_port() -> int:
    """Return an available TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_server(url: str, timeout: float = 15.0, interval: float = 0.5) -> bool:
    """Poll *url* until an HTTP response is received or *timeout* seconds pass."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            requests.get(url, timeout=1)
            return True
        except requests.exceptions.ConnectionError:
            time.sleep(interval)
        except Exception:
            return False
    return False


def validate_srt_timecodes(srt_content: str) -> bool:
    """Check SRT has valid timecode format."""
    pattern = r"\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}"
    return bool(re.search(pattern, srt_content))


@skip_no_e2e
@skip_no_ffmpeg
@pytest.mark.slow
@pytest.mark.e2e
def test_cli_without_translation():
    """E2E: CLI generates SRT from synthetic video."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output = Path(tmpdir) / "output.srt"
        result = subprocess.run(
            [
                sys.executable,
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


@skip_no_e2e
@skip_no_ffmpeg
@pytest.mark.skipif(
    not _argos_pair_installed("en", "es"),
    reason="Argos en→es translation package not installed",
)
@pytest.mark.slow
@pytest.mark.e2e
def test_cli_with_translation():
    """E2E: CLI generates Spanish SRT from English audio."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output = Path(tmpdir) / "output_es.srt"
        result = subprocess.run(
            [
                sys.executable,
                "main.py",
                "--input",
                "tests/fixtures/e2e_test.mp4",
                "--output",
                str(output),
                "--target-lang",
                "es",
                "--source-lang",
                "en",
                "--model",
                "tiny",
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


@skip_no_e2e
@skip_no_ffmpeg
@pytest.mark.slow
@pytest.mark.e2e
def test_api_without_translation():
    """E2E: API endpoint generates SRT from video upload."""
    port = _free_port()

    # Start server in background
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "gensubtitles.api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    base_url = f"http://127.0.0.1:{port}"
    try:
        ready = _wait_for_server(f"{base_url}/docs", timeout=15)
        assert ready, "API server did not start in time"

        # Upload video
        with open("tests/fixtures/e2e_test.mp4", "rb") as f:
            files = {"file": ("test.mp4", f, "video/mp4")}
            response = requests.post(
                f"{base_url}/subtitles", files=files, timeout=120
            )

        assert response.status_code == 200, f"API failed: {response.text}"
        assert response.headers["content-type"] == "text/plain; charset=utf-8"

        srt_content = response.text
        assert validate_srt_timecodes(srt_content), "No valid timecodes in SRT"
        assert len(srt_content) > 10, "SRT too short"

    finally:
        proc.terminate()
        proc.wait(timeout=5)
