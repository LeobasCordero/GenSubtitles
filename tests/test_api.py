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
        with patch("gensubtitles.api.main.WhisperTranscriber", return_value=mock_transcriber), TestClient(app) as c:
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
        import time

        mock_transcriber_instance = MagicMock()

        with (
            patch("gensubtitles.api.main.WhisperTranscriber", return_value=mock_transcriber_instance) as mock_cls,
            patch("huggingface_hub.snapshot_download"),
        ):
            with TestClient(app) as lifespan_client:
                # Model loading happens in a background thread; poll /status until ready
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    resp = lifespan_client.get("/status")
                    if resp.json().get("stage") == "ready":
                        break
                    time.sleep(0.1)
                # After startup, transcriber is on app.state
                assert app.state.transcriber is mock_transcriber_instance
            # After shutdown, transcriber is released
            assert app.state.transcriber is None

        # WhisperTranscriber was instantiated exactly once (not per-request)
        mock_cls.assert_called_once()


class TestGetLanguages:
    """Phase 9 — covers API-05 (GET /languages) and API-07 (OpenAPI docs)."""

    def test_get_languages_returns_200_with_pairs_key(self, client):
        """GET /languages returns HTTP 200 with a JSON body containing a 'pairs' key."""
        with patch("gensubtitles.core.translator.list_installed_pairs", return_value=[]):
            response = client.get("/languages")
        assert response.status_code == 200
        body = response.json()
        assert "pairs" in body
        assert isinstance(body["pairs"], list)

    def test_get_languages_empty_when_no_models(self, client):
        """GET /languages with no installed models returns {'pairs': []}."""
        with patch("gensubtitles.core.translator.list_installed_pairs", return_value=[]):
            response = client.get("/languages")
        assert response.status_code == 200
        assert response.json() == {"pairs": []}

    def test_get_languages_with_pairs(self, client):
        """GET /languages with installed pairs returns them in the response body."""
        fake_pairs = [{"from": "en", "to": "es"}, {"from": "en", "to": "fr"}]
        with patch("gensubtitles.core.translator.list_installed_pairs", return_value=fake_pairs):
            response = client.get("/languages")
        assert response.status_code == 200
        assert response.json() == {"pairs": fake_pairs}

    def test_cors_header_present(self, client):
        """CORS Access-Control-Allow-Origin header is present on API responses."""
        with patch("gensubtitles.core.translator.list_installed_pairs", return_value=[]):
            response = client.get("/languages", headers={"Origin": "http://localhost"})
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers

    def test_openapi_json_includes_both_endpoints(self, client):
        """GET /openapi.json is valid JSON and includes paths for /subtitles and /languages."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "/languages" in schema["paths"]
        assert "/subtitles" in schema["paths"]

    def test_docs_returns_200(self, client):
        """GET /docs returns HTTP 200 (Swagger UI accessible)."""
        response = client.get("/docs")
        assert response.status_code == 200


class TestGetProgress:
    """Tests for the GET /progress endpoint."""

    def _reset_progress(self):
        """Reset module-level progress state to idle."""
        from gensubtitles.api.routers.subtitles import _set_progress
        _set_progress("idle", "Idle", 0, 0)

    def test_progress_returns_200_with_expected_schema(self, client):
        """GET /progress returns HTTP 200 with stage/current/total/label keys."""
        self._reset_progress()
        response = client.get("/progress")
        assert response.status_code == 200
        body = response.json()
        assert "stage" in body
        assert "current" in body
        assert "total" in body
        assert "label" in body

    def test_progress_idle_by_default(self, client):
        """GET /progress returns idle state when no job is running."""
        self._reset_progress()
        response = client.get("/progress")
        assert response.status_code == 200
        body = response.json()
        assert body["stage"] == "idle"

    def test_progress_reflects_updates_during_subtitles_request(self, client, video_bytes):
        """GET /progress reflects stage updates set during POST /subtitles."""
        self._reset_progress()

        # Before any request, should be idle
        resp_before = client.get("/progress")
        assert resp_before.json()["stage"] == "idle"

        # After a subtitle request completes, progress should be "done"
        response = client.post(
            "/subtitles",
            files={"file": ("video.mp4", video_bytes, "video/mp4")},
        )
        assert response.status_code == 200
        resp_after = client.get("/progress")
        assert resp_after.json()["stage"] == "done"
        assert resp_after.json()["label"] == "✓ Done"

    def test_progress_shows_error_on_pipeline_failure(self, client):
        """GET /progress reflects 'error' stage when the pipeline fails."""
        self._reset_progress()

        def raising_extract(video_path, wav_path):
            raise RuntimeError("FFmpeg cannot decode this stream")

        with patch("gensubtitles.core.audio.extract_audio", side_effect=raising_extract):
            response = client.post(
                "/subtitles",
                files={"file": ("bad.mp4", b"not a video", "video/mp4")},
            )
        assert response.status_code in (400, 500)

        resp_after = client.get("/progress")
        assert resp_after.json()["stage"] == "error"
        assert "failed" in resp_after.json()["label"].lower()
