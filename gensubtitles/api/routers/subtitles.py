"""
gensubtitles.api.routers.subtitles
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Router for subtitle-generation endpoints.

POST /subtitles
    Accepts a video file upload, copies it to a named temp file (required by
    FFmpeg which needs a real disk path), runs the transcription/translation/SRT
    pipeline using the app-level preloaded WhisperTranscriber, and returns
    the resulting SRT as a FileResponse.

    Route is a sync ``def`` — FastAPI automatically dispatches sync routes to a
    thread pool executor so the async event loop is never blocked.
"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from gensubtitles.api.dependencies import get_transcriber
from gensubtitles.core.transcriber import WhisperTranscriber

router = APIRouter()

# Mirrors SUPPORTED_EXTENSIONS from core.audio — defined here to allow
# early validation before the lazy import (which triggers the FFmpeg check).
_SUPPORTED_VIDEO_EXTENSIONS = frozenset({".mp4", ".mkv", ".avi", ".mov", ".webm"})


@router.post("/subtitles")
def post_subtitles(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    target_lang: Optional[str] = Query(default=None, description="ISO 639-1 target language for translation (e.g. 'es'). Omit to skip translation."),
    source_lang: Optional[str] = Query(default=None, description="Force source language detection (e.g. 'en'). Omit for auto-detect."),
    transcriber: WhisperTranscriber = Depends(get_transcriber),
) -> FileResponse:
    """
    Upload a video file and receive an SRT subtitle file in response.

    Accepts any video format supported by FFmpeg (mp4, mkv, avi, mov, webm).
    Transcription runs in FastAPI's thread pool — does not block the async event loop.
    """
    # ── 0. Validate file extension before touching disk ────────────────────────
    video_suffix = Path(file.filename or "").suffix.lower()
    if video_suffix not in _SUPPORTED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported video format '{video_suffix}'. "
                f"Supported formats: {', '.join(sorted(_SUPPORTED_VIDEO_EXTENSIONS))}"
            ),
        )

    # ── 1. Copy UploadFile → NamedTemporaryFile on disk ───────────────────────
    # FFmpeg requires a real file path; UploadFile is an in-memory spoolfile.
    tmp_video = tempfile.NamedTemporaryFile(delete=False, suffix=video_suffix)
    try:
        shutil.copyfileobj(file.file, tmp_video)
    finally:
        tmp_video.flush()
        tmp_video.close()
        file.file.close()

    video_path = Path(tmp_video.name)
    background_tasks.add_task(video_path.unlink, missing_ok=True)

    # ── 2. Temp file for SRT output ────────────────────────────────────────────
    tmp_srt = tempfile.NamedTemporaryFile(delete=False, suffix=".srt")
    tmp_srt.close()
    srt_path = Path(tmp_srt.name)
    background_tasks.add_task(srt_path.unlink, missing_ok=True)

    # ── 3. Run pipeline using preloaded transcriber ────────────────────────────
    # audio_temp_context() manages the intermediate WAV file lifecycle.
    # Lazy imports avoid import-time FFmpeg check when tests mock these functions.
    from gensubtitles.core.audio import audio_temp_context, extract_audio  # noqa: PLC0415
    from gensubtitles.core.srt_writer import write_srt  # noqa: PLC0415
    with audio_temp_context() as wav_path:
        extract_audio(video_path, wav_path)
        transcription = transcriber.transcribe(wav_path, language=source_lang)

    segments = transcription.segments
    detected_lang = transcription.language

    # ── 4. Optional translation ────────────────────────────────────────────────
    if target_lang is not None and target_lang != detected_lang:
        from gensubtitles.core.translator import translate_segments  # noqa: PLC0415
        segments = translate_segments(segments, detected_lang, target_lang)

    # ── 5. Write SRT ───────────────────────────────────────────────────────────
    write_srt(segments, srt_path)

    # ── 6. Return as FileResponse ──────────────────────────────────────────────
    # BackgroundTasks (registered above) will delete both temp files after the
    # response body is fully sent to the client.
    return FileResponse(
        path=str(srt_path),
        media_type="text/plain; charset=utf-8",
        filename="subtitles.srt",
    )


@router.get("/languages")
def get_languages() -> dict:
    """
    Return all installed Argos Translate language pairs.

    Returns an empty list if no translation models are installed yet.
    """
    from gensubtitles.core.translator import list_installed_pairs  # noqa: PLC0415

    return {"pairs": list_installed_pairs()}
