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

import sys
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
    mock_translate = MagicMock(return_value=translate_return or segments)
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

    mocks["translate_segments"].assert_called_once_with(segments, "fr", "es")


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
