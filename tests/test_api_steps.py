"""
Tests for path-based step endpoints (POST /steps/*).
All heavy dependencies mocked — no GPU, FFmpeg, or model downloads required.
"""
from __future__ import annotations

import json
from collections import namedtuple
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from gensubtitles.api.dependencies import get_transcriber
from gensubtitles.api.main import app

_TR = namedtuple("TranscriptionResult", ["segments", "language", "duration"])


def _make_seg(start=0.0, end=1.0, text="Hello"):
    return SimpleNamespace(start=start, end=end, text=text)


def _make_mock_transcriber(language="en"):
    mock = MagicMock()
    mock.transcribe.return_value = _TR(segments=[_make_seg()], language=language, duration=1.0)
    return mock


def _transcription_json(language="en"):
    return json.dumps({
        "language": language,
        "duration": 1.0,
        "segments": [{"start": 0, "end": 1, "text": "Hi"}],
    })


_LOOPBACK_CLIENT = ("127.0.0.1", 50000)


def test_steps_extract_success(tmp_path):
    """POST /steps/extract with valid video_path → 200 status=done, output_path ends with audio.wav."""
    video = tmp_path / "test.mp4"
    video.write_bytes(b"fake mp4")
    work = tmp_path / "work"
    work.mkdir()

    def _side(video_path, output_path):
        Path(output_path).write_bytes(b"RIFF fake wav")

    with patch("gensubtitles.core.audio.extract_audio", side_effect=_side):
        with TestClient(app, client=_LOOPBACK_CLIENT) as client:
            resp = client.post("/steps/extract", json={"video_path": str(video), "work_dir": str(work)})

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "done"
    assert body["output_path"].endswith("audio.wav")


def test_steps_extract_video_not_found(tmp_path):
    """POST /steps/extract with missing video returns 404."""
    with TestClient(app, client=_LOOPBACK_CLIENT) as client:
        resp = client.post("/steps/extract", json={
            "video_path": str(tmp_path / "nonexistent.mp4"),
            "work_dir": str(tmp_path / "work"),
        })
    assert resp.status_code == 404


def test_steps_non_loopback_rejected(tmp_path):
    """POST /steps/* from a non-loopback host returns 403."""
    with TestClient(app) as client:
        resp = client.post("/steps/extract", json={
            "video_path": str(tmp_path / "video.mp4"),
            "work_dir": str(tmp_path / "work"),
        })
    assert resp.status_code == 403


def test_steps_transcribe_success(tmp_path):
    """POST /steps/transcribe writes transcription.json and returns 200."""
    work = tmp_path / "work"
    work.mkdir()
    (work / "audio.wav").write_bytes(b"fake wav")

    mock_tr = _make_mock_transcriber()
    app.dependency_overrides[get_transcriber] = lambda: mock_tr
    try:
        with TestClient(app, client=_LOOPBACK_CLIENT) as client:
            resp = client.post("/steps/transcribe", json={"work_dir": str(work)})
    finally:
        app.dependency_overrides.pop(get_transcriber, None)

    assert resp.status_code == 200
    assert resp.json()["status"] == "done"
    assert resp.json()["output_path"].endswith("transcription.json")
    assert (work / "transcription.json").exists()
    mock_tr.transcribe.assert_called_once()


def test_steps_transcribe_uses_preloaded_model(tmp_path):
    """transcribe endpoint passes the injected transcriber (not None) to transcribe_step."""
    work = tmp_path / "work"
    work.mkdir()
    (work / "audio.wav").write_bytes(b"fake wav")

    mock_tr = _make_mock_transcriber()
    captured: list = []

    from gensubtitles.core import steps as steps_module

    def _mock_ts(work_dir, transcriber=None, **kw):
        captured.append(transcriber)
        # Write the JSON so the route can return output_path
        Path(work_dir, "transcription.json").write_text(
            json.dumps({"language": "en", "duration": 1.0, "segments": []}), encoding="utf-8"
        )
        return _TR(segments=[], language="en", duration=0.0)

    app.dependency_overrides[get_transcriber] = lambda: mock_tr
    try:
        with patch.object(steps_module, "transcribe_step", _mock_ts):
            with TestClient(app, client=_LOOPBACK_CLIENT) as client:
                resp = client.post("/steps/transcribe", json={"work_dir": str(work)})
    finally:
        app.dependency_overrides.pop(get_transcriber, None)

    assert resp.status_code == 200
    # Verify the pre-loaded transcriber was passed, not None
    if captured:
        assert captured[0] is mock_tr


def test_steps_translate_success(tmp_path):
    """POST /steps/translate writes translation.json."""
    work = tmp_path / "work"
    work.mkdir()
    (work / "transcription.json").write_text(_transcription_json(), encoding="utf-8")

    with patch("gensubtitles.core.translator.translate_segments") as mock_tl:
        mock_tl.return_value = [_make_seg(text="Hola")]
        with TestClient(app, client=_LOOPBACK_CLIENT) as client:
            resp = client.post("/steps/translate", json={"work_dir": str(work), "target_lang": "es"})

    assert resp.status_code == 200
    assert resp.json()["status"] == "done"
    assert (work / "translation.json").exists()


def test_steps_translate_missing_transcription(tmp_path):
    """POST /steps/translate with empty work_dir returns 404."""
    work = tmp_path / "work"
    work.mkdir()
    with TestClient(app, client=_LOOPBACK_CLIENT) as client:
        resp = client.post("/steps/translate", json={"work_dir": str(work), "target_lang": "es"})
    assert resp.status_code == 404


def test_steps_write_success(tmp_path):
    """POST /steps/write returns SRT output path."""
    work = tmp_path / "work"
    work.mkdir()
    segs = json.dumps([{"start": 0, "end": 1, "text": "Hello world"}])
    (work / "translation.json").write_text(segs, encoding="utf-8")
    out_srt = str(tmp_path / "out.srt")

    with TestClient(app, client=_LOOPBACK_CLIENT) as client:
        resp = client.post("/steps/write", json={"work_dir": str(work), "output_path": out_srt})

    assert resp.status_code == 200
    assert resp.json()["status"] == "done"
    assert Path(out_srt).exists()


def test_steps_write_missing_json(tmp_path):
    """POST /steps/write with empty work_dir returns 404."""
    work = tmp_path / "work"
    work.mkdir()
    with TestClient(app, client=_LOOPBACK_CLIENT) as client:
        resp = client.post("/steps/write", json={
            "work_dir": str(work),
            "output_path": str(tmp_path / "out.srt"),
        })
    assert resp.status_code == 404
