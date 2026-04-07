"""
Phase 8 API tests — covers API-01, API-02, API-04.

All heavy dependencies (FFmpeg, WhisperTranscriber, argostranslate) are mocked
so tests run without GPU, FFmpeg installation, or model downloads.

Note: API-03 (sync route does not block the event loop) is verified by
architecture — ``post_subtitles`` is defined as a plain ``def``, which
FastAPI automatically dispatches to a thread pool executor.
"""
from __future__ import annotations

import sys
import textwrap
from collections import namedtuple
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from gensubtitles.api.dependencies import get_transcriber
from gensubtitles.api.main import app


# ── test helpers ──────────────────────────────────────────────────────────────

_TR = namedtuple("TranscriptionResult", ["segments", "language", "duration"])


def _make_segment(start=0.0, end=1.0, text="Hello world"):
    return SimpleNamespace(start=start, end=end, text=text)


def _fake_srt_content():
    return textwrap.dedent("""\
        1
        00:00:00,000 --> 00:00:01,000
        Hello world

    """)


def _make_mock_transcriber(segments=None, language="en"):
    """Return a MagicMock WhisperTranscriber that returns fake transcription."""
    if segments is None:
        segments = [_make_segment()]
    mock = MagicMock()
    mock.transcribe.return_value = _TR(segments=segments, language=language, duration=1.0)
    return mock


@contextmanager
def _fake_audio_temp_context():
    """Fake audio_temp_context that yields a dummy path without touching disk."""
    yield Path("/tmp/fake_audio.wav")


def _make_mock_audio_module() -> ModuleType:
    """
    Build a fake gensubtitles.core.audio module that can be injected into
    sys.modules. Avoids the import-time FFmpeg availability check in the real module.
    """
    mod = ModuleType("gensubtitles.core.audio")
    mod.extract_audio = MagicMock()  # type: ignore[attr-defined]
    mod.audio_temp_context = _fake_audio_temp_context  # type: ignore[attr-defined]
    return mod


def _make_mock_srt_writer_module() -> ModuleType:
    """Build a fake gensubtitles.core.srt_writer module."""
    mod = ModuleType("gensubtitles.core.srt_writer")

    def fake_write_srt(segments, output_path):
        Path(output_path).write_text(_fake_srt_content(), encoding="utf-8")

    mod.write_srt = fake_write_srt  # type: ignore[attr-defined]
    return mod


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_transcriber():
    return _make_mock_transcriber()


@pytest.fixture
def client(mock_transcriber):
    """
    TestClient with dependency override — no real model loading.

    Injects mock modules for gensubtitles.core.audio and
    gensubtitles.core.srt_writer into sys.modules BEFORE any lazy import
    in the router executes. This bypasses the import-time FFmpeg check in
    audio.py without requiring FFmpeg to be installed.

    Uses the context-manager form of TestClient so lifespan startup/shutdown
    run reliably and resources are cleaned up between tests.
    """
    app.dependency_overrides[get_transcriber] = lambda: mock_transcriber

    mock_audio = _make_mock_audio_module()
    mock_srt = _make_mock_srt_writer_module()

    # Save prior state (None if not yet imported)
    prev_audio = sys.modules.get("gensubtitles.core.audio")
    prev_srt = sys.modules.get("gensubtitles.core.srt_writer")

    sys.modules["gensubtitles.core.audio"] = mock_audio
    sys.modules["gensubtitles.core.srt_writer"] = mock_srt

    try:
        with patch("gensubtitles.api.main.WhisperTranscriber", return_value=mock_transcriber):
            with TestClient(app) as c:
                yield c
    finally:
        app.dependency_overrides.clear()
        # Restore prior sys.modules state
        if prev_audio is None:
            sys.modules.pop("gensubtitles.core.audio", None)
        else:
            sys.modules["gensubtitles.core.audio"] = prev_audio
        if prev_srt is None:
            sys.modules.pop("gensubtitles.core.srt_writer", None)
        else:
            sys.modules["gensubtitles.core.srt_writer"] = prev_srt


@pytest.fixture
def video_bytes():
    """Minimal non-empty bytes representing a fake video upload."""
    return b"FAKE_VIDEO_CONTENT_0001"


# ── tests ─────────────────────────────────────────────────────────────────────

class TestPostSubtitles:

    def test_valid_upload_returns_200_and_srt(self, client, video_bytes):
        """API-01: POST /subtitles with valid upload returns 200 and SRT content."""
        response = client.post(
            "/subtitles",
            files={"file": ("video.mp4", video_bytes, "video/mp4")},
        )
        assert response.status_code == 200
        body = response.text
        # Valid SRT has at minimum: index, timecode arrow, text
        assert "-->" in body

    def test_no_target_lang_skips_translation(self, client, video_bytes):
        """API-01: Without target_lang, translate_segments is never called."""
        with patch("gensubtitles.core.translator.translate_segments") as mock_translate:
            response = client.post(
                "/subtitles",
                files={"file": ("video.mp4", video_bytes, "video/mp4")},
            )
        assert response.status_code == 200
        mock_translate.assert_not_called()

    def test_preloaded_transcriber_used_regardless_of_query_params(self, client, mock_transcriber, video_bytes):
        """API-01: The preloaded transcriber is used for every request; no per-request model loading."""
        response = client.post(
            "/subtitles",
            files={"file": ("video.mp4", video_bytes, "video/mp4")},
        )
        assert response.status_code == 200
        # transcriber.transcribe was called (preloaded model used)
        mock_transcriber.transcribe.assert_called_once()

    def test_upload_file_copied_to_disk_before_extract(self, client, video_bytes):
        """API-02: UploadFile is materialized to a real temp file on disk before extract_audio."""
        captured_path = {}

        def capturing_extract(video_path, wav_path):
            captured_path["video"] = str(video_path)

        with patch("gensubtitles.core.audio.extract_audio", side_effect=capturing_extract):
            response = client.post(
                "/subtitles",
                files={"file": ("video.mp4", video_bytes, "video/mp4")},
            )
        assert response.status_code == 200
        # The path passed to extract_audio must be a real file path (not spooled memory path)
        assert "video" in captured_path
        # Path must have the original file extension
        assert captured_path["video"].endswith(".mp4")

    def test_temp_files_deleted_after_response(self, client, video_bytes):
        """UAT 6: No temp video or SRT files remain on disk after the response is returned."""
        captured_paths: list[str] = []

        def capturing_extract(video_path, wav_path):
            captured_paths.append(str(video_path))

        def capturing_write_srt(segments, output_path):
            captured_paths.append(str(output_path))
            Path(output_path).write_text(_fake_srt_content(), encoding="utf-8")

        with (
            patch("gensubtitles.core.audio.extract_audio", side_effect=capturing_extract),
            patch("gensubtitles.core.srt_writer.write_srt", side_effect=capturing_write_srt),
        ):
            response = client.post(
                "/subtitles",
                files={"file": ("video.mp4", video_bytes, "video/mp4")},
            )

        assert response.status_code == 200
        assert len(captured_paths) == 2, f"Expected 2 temp paths, got: {captured_paths}"
        for path in captured_paths:
            assert not Path(path).exists(), f"Temp file still exists: {path}"

    def test_unsupported_extension_returns_400_json(self, client):
        """Unsupported file extension (e.g. .txt) returns JSON 400 before touching disk."""
        response = client.post(
            "/subtitles",
            files={"file": ("document.txt", b"not a video", "text/plain")},
        )
        assert response.status_code == 400
        body = response.json()
        assert "detail" in body
        assert ".txt" in body["detail"]

    def test_invalid_file_returns_error_json(self, client):
        """UAT 5: Invalid upload that triggers a pipeline error returns JSON with 'detail' key."""
        def raising_extract(video_path, wav_path):
            raise RuntimeError("FFmpeg cannot decode this stream")

        with patch("gensubtitles.core.audio.extract_audio", side_effect=raising_extract):
            response = client.post(
                "/subtitles",
                files={"file": ("bad.mp4", b"not a video", "video/mp4")},
            )
        # Must return JSON with detail key — not a raw 500 stack trace
        assert response.status_code in (400, 500)
        body = response.json()
        assert "detail" in body

    def test_target_lang_triggers_translation(self, client, video_bytes):
        """API-01: When target_lang differs from detected language, translate_segments IS called."""
        fake_segments = [_make_segment(text="Hello")]
        mock_tx = _make_mock_transcriber(segments=fake_segments, language="en")
        app.dependency_overrides[get_transcriber] = lambda: mock_tx

        with patch("gensubtitles.core.translator.translate_segments", return_value=fake_segments) as mock_t:
            response = client.post(
                "/subtitles?target_lang=es",
                files={"file": ("video.mp4", video_bytes, "video/mp4")},
            )
        assert response.status_code == 200
        mock_t.assert_called_once()


class TestLifespan:

    def test_lifespan_sets_transcriber_on_app_state(self):
        """API-04: lifespan loads WhisperTranscriber exactly once and stores it on app.state."""
        mock_transcriber_instance = MagicMock()

        with patch("gensubtitles.api.main.WhisperTranscriber", return_value=mock_transcriber_instance) as mock_cls:
            with TestClient(app) as lifespan_client:
                # After startup, transcriber is on app.state
                assert app.state.transcriber is mock_transcriber_instance
            # After shutdown, transcriber is released
            assert app.state.transcriber is None

        # WhisperTranscriber was instantiated exactly once (not per-request)
        mock_cls.assert_called_once()
