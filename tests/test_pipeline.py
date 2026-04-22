"""
Phase 6 pipeline tests — covers TDD for run_pipeline().

All tests mock sub-module functions (extract_audio, audio_temp_context,
WhisperTranscriber, translate_segments, write_srt) using unittest.mock so tests
run without FFmpeg, GPU, or model downloads.

audio.py raises EnvironmentError at import time when FFmpeg is absent, so tests
inject a fake gensubtitles.core.audio module via sys.modules (the same pattern
used in test_transcriber.py for faster_whisper).
"""
from __future__ import annotations

import types
from collections import namedtuple
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from gensubtitles.core.pipeline import PipelineResult, run_pipeline
from gensubtitles.exceptions import PipelineError


# ── helpers ───────────────────────────────────────────────────────────────────

_TR = namedtuple("_TranscriptionResult", ["segments", "language", "duration"])


def _make_segment(start: float = 0.0, end: float = 1.0, text: str = "Hello"):
    return SimpleNamespace(start=start, end=end, text=text)


def _make_fake_audio_module(
    extract_audio_mock=None,
    audio_temp_context_fn=None,
):
    """Build a fake gensubtitles.core.audio module for sys.modules injection."""
    fake = types.ModuleType("gensubtitles.core.audio")
    if audio_temp_context_fn is None:
        @contextmanager
        def _default_ctx():
            yield Path("fake_temp.wav")
        audio_temp_context_fn = _default_ctx
    fake.audio_temp_context = audio_temp_context_fn
    fake.extract_audio = extract_audio_mock or MagicMock()
    return fake


def _make_fake_transcriber_module(WhisperTranscriber_cls=None):
    """Build a fake gensubtitles.core.transcriber module."""
    fake = types.ModuleType("gensubtitles.core.transcriber")
    fake.WhisperTranscriber = WhisperTranscriber_cls or MagicMock()
    return fake


def _make_fake_translator_module(translate_fn=None):
    """Build a fake gensubtitles.core.translator module."""
    fake = types.ModuleType("gensubtitles.core.translator")
    fake.translate_segments = translate_fn or MagicMock()
    return fake


def _make_fake_srt_writer_module(write_srt_fn=None):
    """Build a fake gensubtitles.core.srt_writer module."""
    fake = types.ModuleType("gensubtitles.core.srt_writer")
    fake.write_srt = write_srt_fn or MagicMock()
    return fake


def _make_mocks(
    segments=None,
    language: str = "en",
    duration: float = 120.0,
    translate_return=None,
):
    """Return a dict of pre-wired mock objects and injected sys.modules fakes."""
    if segments is None:
        segments = [_make_segment()]

    mock_transcription = _TR(segments=segments, language=language, duration=duration)
    mock_transcriber_instance = MagicMock()
    mock_transcriber_instance.transcribe.return_value = mock_transcription
    mock_WhisperTranscriber = MagicMock(return_value=mock_transcriber_instance)
    mock_extract_audio = MagicMock()
    mock_translate = MagicMock(
        return_value=segments if translate_return is None else translate_return
    )
    mock_write_srt = MagicMock()

    @contextmanager
    def fake_audio_temp_context():
        yield Path("fake_temp.wav")

    return {
        "audio_module": _make_fake_audio_module(
            extract_audio_mock=mock_extract_audio,
            audio_temp_context_fn=fake_audio_temp_context,
        ),
        "transcriber_module": _make_fake_transcriber_module(mock_WhisperTranscriber),
        "translator_module": _make_fake_translator_module(mock_translate),
        "srt_writer_module": _make_fake_srt_writer_module(mock_write_srt),
        "extract_audio": mock_extract_audio,
        "WhisperTranscriber": mock_WhisperTranscriber,
        "transcriber_instance": mock_transcriber_instance,
        "translate_segments": mock_translate,
        "write_srt": mock_write_srt,
    }


def _sys_modules_patches(mocks: dict) -> dict:
    """Return the sys.modules injection dict for all pipeline deps."""
    return {
        "gensubtitles.core.audio": mocks["audio_module"],
        "gensubtitles.core.transcriber": mocks["transcriber_module"],
        "gensubtitles.core.translator": mocks["translator_module"],
        "gensubtitles.core.srt_writer": mocks["srt_writer_module"],
    }


# ── test 1 — returns PipelineResult ──────────────────────────────────────────


def test_returns_pipeline_result(tmp_path):
    """run_pipeline returns a PipelineResult with srt_path, detected_language,
    segment_count, and audio_duration_seconds populated correctly."""
    video = tmp_path / "video.mp4"
    video.touch()
    output = tmp_path / "out.srt"
    mocks = _make_mocks(segments=[_make_segment(), _make_segment()], language="fr", duration=90.0)

    with patch.dict("sys.modules", _sys_modules_patches(mocks)):
        result = run_pipeline(str(video), str(output))

    assert isinstance(result, PipelineResult)
    assert result.detected_language == "fr"
    assert result.segment_count == 2
    assert result.audio_duration_seconds == 90.0


# ── test 2 — progress_callback called 4 times ────────────────────────────────


def test_progress_callback_called_four_times(tmp_path):
    """progress_callback is called exactly 4 times with total=4 and
    current values [1, 2, 3, 4] in order."""
    video = tmp_path / "video.mp4"
    video.touch()
    output = tmp_path / "out.srt"
    mocks = _make_mocks()
    calls_received: list[tuple] = []

    def capture(label: str, current: int, total: int) -> None:
        calls_received.append((label, current, total))

    with patch.dict("sys.modules", _sys_modules_patches(mocks)):
        run_pipeline(str(video), str(output), progress_callback=capture)

    assert len(calls_received) == 4
    assert [c[1] for c in calls_received] == [1, 2, 3, 4]
    assert all(c[2] == 4 for c in calls_received)


# ── test 3 — translation skipped when target_lang=None ───────────────────────


def test_translation_skipped_when_no_target_lang(tmp_path):
    """translate_segments is NOT called when target_lang=None and callback
    emits 'Translation skipped' at stage 3."""
    video = tmp_path / "video.mp4"
    video.touch()
    output = tmp_path / "out.srt"
    mocks = _make_mocks()
    calls_received: list[tuple] = []

    def capture(label: str, current: int, total: int) -> None:
        calls_received.append((label, current, total))

    with patch.dict("sys.modules", _sys_modules_patches(mocks)):
        run_pipeline(str(video), str(output), target_lang=None, progress_callback=capture)

    mocks["translate_segments"].assert_not_called()
    stage3_label = calls_received[2][0]
    assert stage3_label == "Translation skipped"


# ── test 4 — translation runs when target_lang provided ──────────────────────


def test_translation_runs_when_target_lang_provided(tmp_path):
    """translate_segments IS called with (segments, detected_language, target_lang)."""
    segments = [_make_segment(text="Bonjour")]
    video = tmp_path / "video.mp4"
    video.touch()
    output = tmp_path / "out.srt"
    mocks = _make_mocks(segments=segments, language="fr")

    with patch.dict("sys.modules", _sys_modules_patches(mocks)):
        run_pipeline(str(video), str(output), target_lang="es")

    mocks["translate_segments"].assert_called_once_with(segments, "fr", "es", engine="argos")


# ── test 5 — FileNotFoundError for missing video ─────────────────────────────


def test_file_not_found_raised_for_missing_video(tmp_path):
    """FileNotFoundError is raised before any audio extraction when video does not exist."""
    missing = tmp_path / "nonexistent.mp4"
    output = tmp_path / "out.srt"
    mocks = _make_mocks()

    with patch.dict("sys.modules", _sys_modules_patches(mocks)):
        with pytest.raises(FileNotFoundError, match="nonexistent"):
            run_pipeline(str(missing), str(output))

    mocks["extract_audio"].assert_not_called()


# ── test 6 — temp file cleanup on success ────────────────────────────────────


def test_temp_file_cleanup_on_success(tmp_path):
    """audio_temp_context __exit__ is called — temp file is cleaned up after success."""
    video = tmp_path / "video.mp4"
    video.touch()
    output = tmp_path / "out.srt"
    cleanup_called: list[bool] = []

    @contextmanager
    def tracking_context():
        yield Path("fake_temp.wav")
        cleanup_called.append(True)

    mocks = _make_mocks()
    tracking_audio_module = _make_fake_audio_module(
        extract_audio_mock=mocks["extract_audio"],
        audio_temp_context_fn=tracking_context,
    )
    patched_modules = {**_sys_modules_patches(mocks), "gensubtitles.core.audio": tracking_audio_module}

    with patch.dict("sys.modules", patched_modules):
        run_pipeline(str(video), str(output))

    assert cleanup_called, "audio_temp_context __exit__ was not called — temp file not cleaned up"


# ── test 6b — temp file cleanup on exception ─────────────────────────────────


def test_temp_file_cleanup_on_exception(tmp_path):
    """audio_temp_context __exit__ is called even when a pipeline stage raises,
    ensuring the temp WAV is cleaned up on error."""
    video = tmp_path / "video.mp4"
    video.touch()
    output = tmp_path / "out.srt"
    cleanup_called: list[bool] = []

    @contextmanager
    def tracking_context():
        try:
            yield Path("fake_temp.wav")
        finally:
            cleanup_called.append(True)

    mocks = _make_mocks()
    mocks["transcriber_instance"].transcribe.side_effect = RuntimeError("boom during transcription")
    tracking_audio_module = _make_fake_audio_module(
        extract_audio_mock=mocks["extract_audio"],
        audio_temp_context_fn=tracking_context,
    )
    patched_modules = {**_sys_modules_patches(mocks), "gensubtitles.core.audio": tracking_audio_module}

    with patch.dict("sys.modules", patched_modules):
        with pytest.raises(PipelineError):
            run_pipeline(str(video), str(output))

    assert cleanup_called, "audio_temp_context __exit__ was not called on exception — temp file leaked"


# ── test 7 — stage exceptions wrapped as PipelineError ───────────────────────


def test_stage_error_wrapped_as_pipeline_error(tmp_path):
    """RuntimeError from WhisperTranscriber.transcribe() is re-raised as PipelineError
    with a stage identifier in the message."""
    video = tmp_path / "video.mp4"
    video.touch()
    output = tmp_path / "out.srt"
    mocks = _make_mocks()
    mocks["transcriber_instance"].transcribe.side_effect = RuntimeError("model boom")

    with patch.dict("sys.modules", _sys_modules_patches(mocks)):
        with pytest.raises(PipelineError) as exc_info:
            run_pipeline(str(video), str(output))

    assert "transcription" in str(exc_info.value).lower()


# ── test 8 — srt_path in PipelineResult matches output_path ──────────────────


def test_srt_path_matches_output_path(tmp_path):
    """result.srt_path equals str(output_path) exactly."""
    video = tmp_path / "video.mp4"
    video.touch()
    output = tmp_path / "output" / "test.srt"
    mocks = _make_mocks()

    with patch.dict("sys.modules", _sys_modules_patches(mocks)):
        result = run_pipeline(str(video), str(output))

    assert result.srt_path == str(output)


# ── TestPipelineCancellation — cancellation check-points in _run_pipeline_job ──


class TestPipelineCancellation:
    """Verify that _run_pipeline_job respects the cancel flag between stages."""

    def _make_job(self, cancelled: bool = False) -> dict:
        """Create a minimal job dict."""
        from queue import Queue
        import threading
        job = {"queue": Queue(), "cancel": threading.Event(), "result": None, "error": None}
        if cancelled:
            job["cancel"].set()
        return job

    def test_cancel_after_extract_stops_pipeline(self, tmp_path):
        """If cancel is set after audio extraction, pipeline stops before transcription."""
        import uuid
        import threading
        import unittest.mock as mock
        from gensubtitles.api.routers import subtitles as sub_mod

        video_path = tmp_path / "v.mp4"
        video_path.write_bytes(b"fake")
        srt_path = tmp_path / "out.srt"

        job_id = str(uuid.uuid4())
        job = self._make_job()
        sub_mod._jobs[job_id] = job

        transcribe_called = threading.Event()

        def _fake_extract(video, wav):
            wav.write_bytes(b"fake wav")
            job["cancel"].set()  # set cancel after extraction

        class FakeTranscriber:
            def transcribe(self, *a, **kw):
                transcribe_called.set()
                raise AssertionError("transcribe should not be called after cancel")

        with mock.patch("gensubtitles.core.audio.extract_audio", _fake_extract):
            with mock.patch("gensubtitles.core.audio.audio_temp_context") as ctx_mock:
                ctx_mock.return_value.__enter__ = lambda *_: tmp_path / "audio.wav"
                ctx_mock.return_value.__exit__ = lambda *_: False
                sub_mod._run_pipeline_job(job_id, video_path, srt_path, None, None, "argos", FakeTranscriber())

        assert not transcribe_called.is_set(), "Transcription should NOT have been called"
        events = []
        while not job["queue"].empty():
            events.append(job["queue"].get_nowait())
        stages = [e.get("stage") for e in events]
        assert "cancelled" in stages, f"Expected cancelled event, got: {stages}"

        sub_mod._jobs.pop(job_id, None)

    def test_cancel_not_set_allows_full_pipeline(self, tmp_path):
        """If cancel is never set, pipeline runs to completion and sets result."""
        import uuid
        import unittest.mock as mock
        from gensubtitles.api.routers import subtitles as sub_mod

        video_path = tmp_path / "v.mp4"
        video_path.write_bytes(b"fake")
        srt_path = tmp_path / "out.srt"
        srt_path.write_text("", encoding="utf-8")

        job_id = str(uuid.uuid4())
        job = self._make_job(cancelled=False)
        sub_mod._jobs[job_id] = job

        class FakeResult:
            segments = []
            language = "en"

        class FakeTranscriber:
            def transcribe(self, *a, **kw):
                return FakeResult()

        with mock.patch("gensubtitles.core.audio.extract_audio", lambda *a: None):
            with mock.patch("gensubtitles.core.audio.audio_temp_context") as ctx_mock:
                ctx_mock.return_value.__enter__ = lambda *_: tmp_path / "audio.wav"
                ctx_mock.return_value.__exit__ = lambda *_: False
                with mock.patch("gensubtitles.core.srt_writer.write_srt", lambda *a: None):
                    sub_mod._run_pipeline_job(job_id, video_path, srt_path, None, None, "argos", FakeTranscriber())

        events = []
        while not job["queue"].empty():
            events.append(job["queue"].get_nowait())
        stages = [e.get("stage") for e in events]
        assert "done" in stages, f"Expected done event, got: {stages}"
        assert "cancelled" not in stages

        sub_mod._jobs.pop(job_id, None)


# ── Phase 12 new tests — transcriber= injection and cancel_event= ─────────────


def test_transcriber_injection_uses_provided_transcriber(tmp_path):
    """When transcriber= is passed, it is used and WhisperTranscriber() is NOT constructed."""
    video = tmp_path / "video.mp4"
    video.touch()
    output = tmp_path / "out.srt"
    mocks = _make_mocks()

    custom_transcriber = MagicMock()
    mock_transcription = _TR(segments=[_make_segment()], language="en", duration=5.0)
    custom_transcriber.transcribe.return_value = mock_transcription

    with patch.dict("sys.modules", _sys_modules_patches(mocks)):
        result = run_pipeline(str(video), str(output), transcriber=custom_transcriber)

    custom_transcriber.transcribe.assert_called_once()
    mocks["WhisperTranscriber"].assert_not_called()
    assert isinstance(result, PipelineResult)


def test_no_transcriber_creates_whisper_internally(tmp_path):
    """When transcriber=None (default), WhisperTranscriber() is constructed internally."""
    video = tmp_path / "video.mp4"
    video.touch()
    output = tmp_path / "out.srt"
    mocks = _make_mocks()

    with patch.dict("sys.modules", _sys_modules_patches(mocks)):
        run_pipeline(str(video), str(output))

    mocks["WhisperTranscriber"].assert_called_once()


def test_cancel_event_set_before_call_raises_pipeline_error(tmp_path):
    """cancel_event already set → PipelineError('[cancelled]') raised before transcription."""
    import threading

    video = tmp_path / "video.mp4"
    video.touch()
    output = tmp_path / "out.srt"
    mocks = _make_mocks()
    cancel = threading.Event()
    cancel.set()

    with patch.dict("sys.modules", _sys_modules_patches(mocks)):
        with pytest.raises(PipelineError, match=r"\[cancelled\]"):
            run_pipeline(str(video), str(output), cancel_event=cancel)

    mocks["transcriber_instance"].transcribe.assert_not_called()


def test_cancel_event_set_during_audio_extraction_stops_before_transcription(tmp_path):
    """cancel_event set inside extract_audio → PipelineError raised; transcription not called."""
    import threading

    video = tmp_path / "video.mp4"
    video.touch()
    output = tmp_path / "out.srt"
    cancel = threading.Event()

    mocks = _make_mocks()

    def _set_cancel_then_extract(video_path, wav_path):
        cancel.set()

    mocks["extract_audio"].side_effect = _set_cancel_then_extract

    with patch.dict("sys.modules", _sys_modules_patches(mocks)):
        with pytest.raises(PipelineError, match=r"\[cancelled\]"):
            run_pipeline(str(video), str(output), cancel_event=cancel)

    mocks["transcriber_instance"].transcribe.assert_not_called()


def test_cancel_event_none_runs_to_completion(tmp_path):
    """cancel_event=None (default) — pipeline runs to full completion."""
    video = tmp_path / "video.mp4"
    video.touch()
    output = tmp_path / "out.srt"
    mocks = _make_mocks()

    with patch.dict("sys.modules", _sys_modules_patches(mocks)):
        result = run_pipeline(str(video), str(output), cancel_event=None)

    assert isinstance(result, PipelineResult)
    mocks["write_srt"].assert_called_once()
