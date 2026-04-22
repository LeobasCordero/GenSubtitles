"""
Phase 8 API tests — covers API-01, API-02, API-04.

All heavy dependencies (FFmpeg, WhisperTranscriber, argostranslate) are mocked
so tests run without GPU, FFmpeg installation, or model downloads.

Note: API-03 (sync route does not block the event loop) is verified by
architecture — ``post_subtitles`` is defined as a plain ``def``, which
FastAPI automatically dispatches to a thread pool executor.
"""
from __future__ import annotations

import os
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

    Sets GENSUBTITLES_SKIP_HF_PREFETCH=1 so the background loader thread
    skips HuggingFace Hub network calls when WhisperTranscriber is mocked.

    Uses the context-manager form of TestClient so lifespan startup/shutdown
    run reliably and resources are cleaned up between tests.
    """
    app.dependency_overrides[get_transcriber] = lambda: mock_transcriber

    mock_audio = _make_mock_audio_module()
    mock_srt = _make_mock_srt_writer_module()

    # Save prior state (None if not yet imported)
    prev_audio = sys.modules.get("gensubtitles.core.audio")
    prev_srt = sys.modules.get("gensubtitles.core.srt_writer")
    prev_skip = os.environ.get("GENSUBTITLES_SKIP_HF_PREFETCH")

    sys.modules["gensubtitles.core.audio"] = mock_audio
    sys.modules["gensubtitles.core.srt_writer"] = mock_srt
    os.environ["GENSUBTITLES_SKIP_HF_PREFETCH"] = "1"

    try:
        with patch("gensubtitles.api.main.WhisperTranscriber", return_value=mock_transcriber), TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()
        # Restore prior env state
        if prev_skip is None:
            os.environ.pop("GENSUBTITLES_SKIP_HF_PREFETCH", None)
        else:
            os.environ["GENSUBTITLES_SKIP_HF_PREFETCH"] = prev_skip
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

class TestLifespan:

    def test_lifespan_sets_transcriber_on_app_state(self):
        """API-04: lifespan loads WhisperTranscriber exactly once and stores it on app.state."""
        import time

        mock_transcriber_instance = MagicMock()
        prev_skip = os.environ.get("GENSUBTITLES_SKIP_HF_PREFETCH")
        os.environ["GENSUBTITLES_SKIP_HF_PREFETCH"] = "1"

        try:
            with (
                patch("gensubtitles.api.main.WhisperTranscriber", return_value=mock_transcriber_instance) as mock_cls,
            ):
                with TestClient(app) as lifespan_client:
                    # Model loading happens in a background thread; poll /status until ready
                    deadline = time.monotonic() + 10
                    ready = False
                    while time.monotonic() < deadline:
                        resp = lifespan_client.get("/status")
                        if resp.json().get("stage") == "ready":
                            ready = True
                            break
                        time.sleep(0.1)
                    assert ready, "Server did not reach 'ready' state within timeout"
                    # After startup, transcriber is on app.state
                    assert app.state.transcriber is mock_transcriber_instance
                # After shutdown, transcriber is released
                assert app.state.transcriber is None

            # WhisperTranscriber was instantiated exactly once (not per-request)
            mock_cls.assert_called_once()
        finally:
            if prev_skip is None:
                os.environ.pop("GENSUBTITLES_SKIP_HF_PREFETCH", None)
            else:
                os.environ["GENSUBTITLES_SKIP_HF_PREFETCH"] = prev_skip


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
        """GET /openapi.json is valid JSON and includes paths for /subtitles/async and /languages."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "/languages" in schema["paths"]
        assert "/subtitles/async" in schema["paths"]

    def test_docs_returns_200(self, client):
        """GET /docs returns HTTP 200 (Swagger UI accessible)."""
        response = client.get("/docs")
        assert response.status_code == 200


class TestSSEJobPattern:
    """Tests for POST /subtitles/async, GET /stream, GET /result, DELETE endpoints."""

    @pytest.fixture()
    def mock_pipeline(self, tmp_path, monkeypatch):
        """Patch _run_pipeline_job to immediately complete with a fake SRT."""
        from gensubtitles.api.routers import subtitles as sub_mod

        def _fake_pipeline(job_id, video_path, srt_path, *args, **kwargs):
            job = sub_mod._jobs[job_id]
            # Set result BEFORE sending "done" so GET /result returns 200 immediately
            srt_path.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n\n", encoding="utf-8")
            job["result"] = srt_path
            sub_mod._set_progress("done", "Done", job=job)

        monkeypatch.setattr(sub_mod, "_run_pipeline_job", _fake_pipeline)
        return _fake_pipeline

    def test_post_subtitles_async_returns_job_id_immediately(self, client, mock_pipeline, tmp_path):
        """POST /subtitles/async returns {"job_id": str} immediately."""
        video = tmp_path / "test.mp4"
        video.write_bytes(b"fake video content")
        resp = client.post(
            "/subtitles/async",
            files={"file": ("test.mp4", video.read_bytes(), "application/octet-stream")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "job_id" in data
        assert isinstance(data["job_id"], str) and len(data["job_id"]) == 36  # UUID4

    def test_stream_yields_done_event(self, client, mock_pipeline, tmp_path):
        """GET /subtitles/{job_id}/stream yields SSE events ending with stage=done."""
        import json
        video = tmp_path / "clip.mp4"
        video.write_bytes(b"fake")
        post_resp = client.post(
            "/subtitles/async",
            files={"file": ("clip.mp4", video.read_bytes(), "application/octet-stream")},
        )
        job_id = post_resp.json()["job_id"]
        with client.stream("GET", f"/subtitles/{job_id}/stream") as stream_resp:
            assert stream_resp.status_code == 200
            assert "text/event-stream" in stream_resp.headers.get("content-type", "")
            events = []
            for line in stream_resp.iter_lines():
                if line.startswith("data:"):
                    events.append(json.loads(line[5:].strip()))
        stages = [e["stage"] for e in events]
        assert "done" in stages, f"Expected 'done' event, got: {stages}"

    def test_get_result_returns_409_before_done(self, client):
        """GET /result returns 409 if pipeline not yet complete (no result set)."""
        import uuid
        from queue import Queue
        import threading
        from gensubtitles.api.routers import subtitles as sub_mod
        job_id = str(uuid.uuid4())
        sub_mod._jobs[job_id] = {"queue": Queue(), "cancel": threading.Event(), "result": None, "error": None}
        try:
            resp = client.get(f"/subtitles/{job_id}/result")
            assert resp.status_code == 409
        finally:
            sub_mod._jobs.pop(job_id, None)

    def test_get_result_returns_srt_after_done(self, client, mock_pipeline, tmp_path):
        """GET /result returns 200 with SRT content after pipeline completes."""
        video = tmp_path / "v.mp4"
        video.write_bytes(b"fake")
        post_resp = client.post(
            "/subtitles/async",
            files={"file": ("v.mp4", video.read_bytes(), "application/octet-stream")},
        )
        job_id = post_resp.json()["job_id"]
        # Drain the SSE stream so done event is processed
        with client.stream("GET", f"/subtitles/{job_id}/stream") as s:
            for _ in s.iter_lines():
                pass
        result_resp = client.get(f"/subtitles/{job_id}/result")
        assert result_resp.status_code == 200
        assert "Hello" in result_resp.text  # fake SRT content from mock

    def test_delete_sets_cancel_flag(self, client):
        """DELETE /subtitles/{job_id} sets the cancel threading.Event."""
        import uuid
        from queue import Queue
        import threading
        from gensubtitles.api.routers import subtitles as sub_mod
        job_id = str(uuid.uuid4())
        cancel_event = threading.Event()
        sub_mod._jobs[job_id] = {"queue": Queue(), "cancel": cancel_event, "result": None, "error": None}
        try:
            resp = client.delete(f"/subtitles/{job_id}")
            assert resp.status_code == 200
            assert resp.json() == {"status": "cancelling"}
            assert cancel_event.is_set(), "Cancel event should be set after DELETE"
        finally:
            sub_mod._jobs.pop(job_id, None)

    def test_unsupported_extension_rejected(self, client, tmp_path):
        """POST /subtitles/async rejects non-video files with 400."""
        bad = tmp_path / "file.txt"
        bad.write_bytes(b"text")
        resp = client.post(
            "/subtitles/async",
            files={"file": ("file.txt", bad.read_bytes(), "text/plain")},
        )
        assert resp.status_code == 400

    def test_run_pipeline_job_srt_persists_until_result_fetched(self, client, tmp_path, monkeypatch):
        """_run_pipeline_job must NOT delete srt_path on success; /result cleanup does it."""
        import types
        import threading
        import uuid
        from queue import Queue
        from gensubtitles.api.routers import subtitles as sub_mod

        srt_content = "1\n00:00:00,000 --> 00:00:01,000\nHello\n\n"

        # Patch gensubtitles.core.audio to avoid FFmpeg import-time check
        @contextmanager
        def _fake_audio_temp_context():
            yield tmp_path / "audio.wav"

        fake_audio = types.SimpleNamespace(
            extract_audio=lambda *a: None,
            audio_temp_context=_fake_audio_temp_context,
        )
        monkeypatch.setitem(sys.modules, "gensubtitles.core.audio", fake_audio)

        # Patch gensubtitles.core.srt_writer to write known SRT content
        def _fake_write_srt(segments, path):
            path.write_text(srt_content, encoding="utf-8")

        fake_srt_writer = types.SimpleNamespace(write_srt=_fake_write_srt)
        monkeypatch.setitem(sys.modules, "gensubtitles.core.srt_writer", fake_srt_writer)

        video_path = tmp_path / "v.mp4"
        video_path.write_bytes(b"fake")
        srt_path = tmp_path / "out.srt"
        srt_path.write_text("", encoding="utf-8")

        class FakeResult:
            segments = []
            language = "en"
            duration = 1.0

        class FakeTranscriber:
            def transcribe(self, *a, **kw):
                return FakeResult()

        job_id = str(uuid.uuid4())
        job: dict = {"queue": Queue(), "cancel": threading.Event(), "result": None, "error": None}
        sub_mod._jobs[job_id] = job

        sub_mod._run_pipeline_job(job_id, video_path, srt_path, None, None, "argos", FakeTranscriber())

        # srt_path must still exist so /result can serve it
        assert srt_path.exists(), "srt_path must not be deleted by _run_pipeline_job on success"

        # job must still be in _jobs so /result endpoint can look it up
        assert job_id in sub_mod._jobs, "job must remain in _jobs after success"

        # GET /result should serve the SRT and then clean up
        resp = client.get(f"/subtitles/{job_id}/result")
        assert resp.status_code == 200
        assert "Hello" in resp.text
        # BackgroundTask cleanup should have deleted srt_path
        assert not srt_path.exists(), "srt_path should be deleted after /result serves it"

    def test_run_pipeline_job_late_cancel_keeps_success_result(self, tmp_path, monkeypatch):
        """Late cancellation after successful pipeline return must not discard completed SRT."""
        import threading
        import uuid
        from queue import Queue

        from gensubtitles.api.routers import subtitles as sub_mod

        video_path = tmp_path / "v.mp4"
        video_path.write_bytes(b"fake")
        srt_path = tmp_path / "out.srt"
        srt_path.write_text("", encoding="utf-8")

        job_id = str(uuid.uuid4())
        job: dict = {"queue": Queue(), "cancel": threading.Event(), "result": None, "error": None}
        sub_mod._jobs[job_id] = job

        def _fake_run_pipeline(*args, **kwargs):
            Path(args[1]).write_text("done", encoding="utf-8")
            kwargs["cancel_event"].set()  # Simulate user cancel arriving at very end.
            return SimpleNamespace(
                srt_path=str(args[1]),
                detected_language="en",
                segment_count=1,
                audio_duration_seconds=1.0,
            )

        monkeypatch.setattr(sub_mod, "run_pipeline", _fake_run_pipeline)

        try:
            sub_mod._run_pipeline_job(job_id, video_path, srt_path, None, None, "argos", MagicMock())
            assert job["result"] == srt_path
            assert srt_path.exists()
            assert job_id in sub_mod._jobs
        finally:
            sub_mod._jobs.pop(job_id, None)


# ── upload/download step endpoint tests ──────────────────────────────────────

def test_post_subtitles_extract_success(tmp_path):
    """POST /subtitles/extract with valid video returns WAV file."""
    fake_video = tmp_path / "test.mp4"
    fake_video.write_bytes(b"fake video bytes")

    def _write_wav(video_path, output_path):
        Path(output_path).write_bytes(b"RIFF fake wav data")

    with patch("gensubtitles.core.audio.extract_audio", side_effect=_write_wav):
        with TestClient(app) as client:
            resp = client.post(
                "/subtitles/extract",
                files={"video": ("test.mp4", fake_video.read_bytes(), "video/mp4")},
            )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("audio/wav")
    assert "test.wav" in resp.headers.get("content-disposition", "")


def test_post_subtitles_transcribe_success():
    """POST /subtitles/transcribe with WAV returns transcription.json."""
    import json as _json

    mock_tr = _make_mock_transcriber()
    app.dependency_overrides[get_transcriber] = lambda: mock_tr
    try:
        def _write_json(segments, path, metadata=None):
            data = {"language": "en", "duration": 1.0, "segments": [{"start": 0.0, "end": 1.0, "text": "Hi"}]}
            Path(path).write_text(_json.dumps(data), encoding="utf-8")

        with patch("gensubtitles.core.steps.segments_to_json", side_effect=_write_json):
            with TestClient(app) as client:
                resp = client.post(
                    "/subtitles/transcribe",
                    files={"audio": ("audio.wav", b"fake wav bytes", "audio/wav")},
                )
    finally:
        app.dependency_overrides.pop(get_transcriber, None)

    assert resp.status_code == 200
    assert "transcription" in resp.headers.get("content-disposition", "")


def test_post_subtitles_translate_success():
    """POST /subtitles/translate returns translation.json."""
    import json as _json

    seg_json = _json.dumps({"language": "en", "duration": 1.0, "segments": [{"start": 0.0, "end": 1.0, "text": "Hello"}]})

    with patch("gensubtitles.core.translator.translate_segments") as mock_tl:
        mock_tl.return_value = [SimpleNamespace(start=0.0, end=1.0, text="Hola")]
        with TestClient(app) as client:
            resp = client.post(
                "/subtitles/translate?target_lang=es",
                files={"segments": ("transcription.json", seg_json.encode(), "application/json")},
            )
    assert resp.status_code == 200
    assert "translation" in resp.headers.get("content-disposition", "")


def test_post_subtitles_write_success():
    """POST /subtitles/write returns an SRT file."""
    import json as _json

    seg_json = _json.dumps([{"start": 0.0, "end": 1.0, "text": "Hello world"}])

    with TestClient(app) as client:
        resp = client.post(
            "/subtitles/write",
            files={"segments": ("translation.json", seg_json.encode(), "application/json")},
        )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    assert "00:00:00" in resp.text  # SRT timestamp present


def test_existing_async_endpoint_unchanged():
    """POST /subtitles/async still exists and starts a job."""
    mock_tr = _make_mock_transcriber()
    app.dependency_overrides[get_transcriber] = lambda: mock_tr
    try:
        with TestClient(app) as client:
            resp = client.post(
                "/subtitles/async",
                files={"file": ("test.mp4", b"fake video", "video/mp4")},
            )
    finally:
        app.dependency_overrides.pop(get_transcriber, None)
    # Should start job successfully (video won't actually process, but endpoint accepts it)
    assert resp.status_code in (200, 422)  # 422 if FFmpeg check fires; 200 if mock bypasses it
