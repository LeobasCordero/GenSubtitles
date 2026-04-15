"""
Tests for gensubtitles.core.steps — stepper mode step functions.

All heavy dependencies (FFmpeg, WhisperTranscriber, argostranslate) are mocked
so tests run without GPU, FFmpeg installation, or model downloads.
"""
from __future__ import annotations

import json
from collections import namedtuple
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from gensubtitles.core.steps import (
    AUDIO_FILENAME,
    TRANSCRIPTION_FILENAME,
    TRANSLATION_FILENAME,
    segments_from_json,
    segments_to_json,
    transcribe_step,
    translate_step,
    write_srt_step,
)

# ── test helpers ──────────────────────────────────────────────────────────────

_TR = namedtuple("TranscriptionResult", ["segments", "language", "duration"])


def _make_seg(start=0.0, end=1.0, text="Hello"):
    return SimpleNamespace(start=start, end=end, text=text)


def _write_transcription_json(work_dir: Path, language: str = "en") -> Path:
    """Write a valid transcription.json (dict format) to work_dir."""
    path = work_dir / TRANSCRIPTION_FILENAME
    data = {
        "language": language,
        "duration": 2.5,
        "segments": [{"start": 0.0, "end": 1.0, "text": "Hello"}],
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _write_translation_json(work_dir: Path) -> Path:
    """Write a valid translation.json (list format) to work_dir."""
    path = work_dir / TRANSLATION_FILENAME
    data = [{"start": 0.0, "end": 1.0, "text": "Hola"}]
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


# ── segments_to_json / segments_from_json ─────────────────────────────────────

def test_segments_roundtrip(tmp_path):
    segs = [_make_seg(0.0, 1.0, "Hello"), _make_seg(1.0, 2.0, "World")]
    path = tmp_path / "segs.json"
    segments_to_json(segs, path)
    result = segments_from_json(path)
    assert len(result) == 2
    assert result[0].start == 0.0
    assert result[0].end == 1.0
    assert result[0].text == "Hello"
    assert result[1].text == "World"


def test_segments_from_json_dict_format(tmp_path):
    path = tmp_path / "transcription.json"
    data = {
        "language": "en",
        "duration": 1.0,
        "segments": [{"start": 0.0, "end": 0.5, "text": "Hi"}],
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    result = segments_from_json(path)
    assert len(result) == 1
    assert result[0].text == "Hi"
    assert result[0].start == 0.0


def test_segments_to_json_metadata(tmp_path):
    segs = [_make_seg()]
    path = tmp_path / "transcription.json"
    segments_to_json(segs, path, metadata={"language": "en", "duration": 1.0})
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(raw, dict)
    assert raw["language"] == "en"
    assert raw["duration"] == 1.0
    assert isinstance(raw["segments"], list)
    assert raw["segments"][0]["text"] == "Hello"


def test_segments_to_json_no_metadata_is_plain_list(tmp_path):
    segs = [_make_seg()]
    path = tmp_path / "translation.json"
    segments_to_json(segs, path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(raw, list)
    assert raw[0]["text"] == "Hello"


# ── extract_audio_step ────────────────────────────────────────────────────────

def test_extract_audio_step_success(tmp_path):
    from gensubtitles.core.steps import extract_audio_step

    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake")

    with patch("gensubtitles.core.audio.extract_audio") as mock_extract:
        result = extract_audio_step(video, tmp_path)

    mock_extract.assert_called_once_with(video, tmp_path / AUDIO_FILENAME)
    assert result == tmp_path / AUDIO_FILENAME


def test_extract_audio_step_missing_video(tmp_path):
    from gensubtitles.core.steps import extract_audio_step

    with pytest.raises(FileNotFoundError, match="Video file not found"):
        extract_audio_step(tmp_path / "nonexistent.mp4", tmp_path)


# ── transcribe_step ───────────────────────────────────────────────────────────

def test_transcribe_step_success(tmp_path):
    (tmp_path / AUDIO_FILENAME).write_bytes(b"fake audio")
    mock_transcriber = MagicMock()
    mock_transcriber.transcribe.return_value = _TR(
        segments=[_make_seg()], language="en", duration=1.0
    )

    result = transcribe_step(tmp_path, transcriber=mock_transcriber)

    assert result.language == "en"
    assert (tmp_path / TRANSCRIPTION_FILENAME).exists()
    raw = json.loads((tmp_path / TRANSCRIPTION_FILENAME).read_text(encoding="utf-8"))
    assert isinstance(raw, dict)
    assert raw["language"] == "en"
    assert isinstance(raw["segments"], list)


def test_transcribe_step_no_wav(tmp_path):
    with pytest.raises(FileNotFoundError, match="audio.wav not found"):
        transcribe_step(tmp_path, transcriber=MagicMock())


def test_transcribe_step_creates_transcriber_when_none(tmp_path):
    (tmp_path / AUDIO_FILENAME).write_bytes(b"fake audio")

    mock_instance = MagicMock()
    mock_instance.transcribe.return_value = _TR(
        segments=[], language="en", duration=0.0
    )

    with patch("gensubtitles.core.transcriber.WhisperTranscriber") as MockClass:
        MockClass.return_value = mock_instance
        transcribe_step(tmp_path, transcriber=None, model_size="tiny", device="cpu")

    MockClass.assert_called_once_with(model_size="tiny", device="cpu")
    mock_instance.transcribe.assert_called_once()


# ── translate_step ────────────────────────────────────────────────────────────

def test_translate_step_success(tmp_path):
    _write_transcription_json(tmp_path, language="en")

    with patch("gensubtitles.core.translator.translate_segments") as mock_tl:
        mock_tl.return_value = [_make_seg(text="Hola")]
        segs = translate_step(tmp_path, target_lang="es")

    assert len(segs) == 1
    assert (tmp_path / TRANSLATION_FILENAME).exists()
    raw = json.loads((tmp_path / TRANSLATION_FILENAME).read_text(encoding="utf-8"))
    assert isinstance(raw, list)
    assert raw[0]["text"] == "Hola"
    mock_tl.assert_called_once()
    call_args = mock_tl.call_args
    assert call_args[0][1] == "en"   # source lang read from JSON metadata
    assert call_args[0][2] == "es"   # target lang


def test_translate_step_missing_transcription(tmp_path):
    with pytest.raises(FileNotFoundError, match="transcription.json not found"):
        translate_step(tmp_path, target_lang="es")


def test_translate_step_missing_language_field(tmp_path):
    """translate_step raises ValueError when transcription.json has no language field."""
    path = tmp_path / TRANSCRIPTION_FILENAME
    path.write_text(json.dumps({"segments": [{"start": 0, "end": 1, "text": "Hi"}]}), encoding="utf-8")

    with pytest.raises(ValueError, match="language"):
        translate_step(tmp_path, target_lang="es")


def test_translate_step_empty_language_field(tmp_path):
    """translate_step raises ValueError when transcription.json has an empty language field."""
    path = tmp_path / TRANSCRIPTION_FILENAME
    path.write_text(json.dumps({"language": "", "segments": [{"start": 0, "end": 1, "text": "Hi"}]}), encoding="utf-8")

    with pytest.raises(ValueError, match="language"):
        translate_step(tmp_path, target_lang="es")


def test_translate_step_flat_list_raises(tmp_path):
    """translate_step raises ValueError for legacy flat-list transcription.json format."""
    path = tmp_path / TRANSCRIPTION_FILENAME
    path.write_text(json.dumps([{"start": 0, "end": 1, "text": "Hi"}]), encoding="utf-8")

    with pytest.raises(ValueError, match="Re-run transcribe_step"):
        translate_step(tmp_path, target_lang="es")


# ── write_srt_step ────────────────────────────────────────────────────────────

def test_write_srt_step_uses_translation_json(tmp_path):
    _write_transcription_json(tmp_path)
    _write_translation_json(tmp_path)
    output = tmp_path / "out.srt"

    with patch("gensubtitles.core.srt_writer.write_srt") as mock_write:
        write_srt_step(tmp_path, output)

    mock_write.assert_called_once()
    segs_arg = mock_write.call_args[0][0]
    # Must come from translation.json ("Hola"), not transcription.json ("Hello")
    assert segs_arg[0].text == "Hola"


def test_write_srt_step_falls_back_to_transcription(tmp_path):
    _write_transcription_json(tmp_path)
    output = tmp_path / "out.srt"

    with patch("gensubtitles.core.srt_writer.write_srt") as mock_write:
        write_srt_step(tmp_path, output)

    mock_write.assert_called_once()
    segs_arg = mock_write.call_args[0][0]
    assert segs_arg[0].text == "Hello"


def test_write_srt_step_no_json(tmp_path):
    with pytest.raises(FileNotFoundError, match="No segments JSON found"):
        write_srt_step(tmp_path, tmp_path / "out.srt")
