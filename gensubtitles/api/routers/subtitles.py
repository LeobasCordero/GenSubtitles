"""
gensubtitles.api.routers.subtitles
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Router for subtitle-generation endpoints.

POST /subtitles/async
    Accepts a video file upload, copies it to a named temp file, starts the
    pipeline in a background thread, and immediately returns a job_id.

GET /subtitles/{job_id}/stream
    Server-Sent Events stream of progress events until done/error/cancelled.

GET /subtitles/{job_id}/result
    Fetch the completed SRT file after the pipeline finishes.

DELETE /subtitles/{job_id}
    Signal cancellation; pipeline stops between stages.
"""
from __future__ import annotations

import asyncio
import json
import shutil
import tempfile
import threading
import uuid
from pathlib import Path
from queue import Queue
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from gensubtitles.api.dependencies import get_transcriber
from gensubtitles.core.transcriber import WhisperTranscriber

router = APIRouter(tags=["subtitles"])

# Mirrors SUPPORTED_EXTENSIONS from core.audio — defined here to allow
# early validation before the lazy import (which triggers the FFmpeg check).
_SUPPORTED_VIDEO_EXTENSIONS = frozenset({".mp4", ".mkv", ".avi", ".mov", ".webm"})

# Module-level progress state (kept for backward compat with any callers)
_progress_lock = threading.Lock()
_progress: dict = {"stage": "idle", "current": 0, "total": 0, "label": "Idle"}

# Per-job state for the async SSE pattern
_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()


def _set_progress(
    stage: str,
    label: str,
    current: int = 0,
    total: int = 0,
    job: dict | None = None,
) -> None:
    with _progress_lock:
        _progress["stage"] = stage
        _progress["label"] = label
        _progress["current"] = current
        _progress["total"] = total
    if job is not None:
        job["queue"].put({"stage": stage, "label": label, "current": current, "total": total})


def _cancel_job(job_id: str, video_path: Path, srt_path: Path) -> None:
    video_path.unlink(missing_ok=True)
    srt_path.unlink(missing_ok=True)
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job:
            job["queue"].put({"stage": "cancelled", "label": "Cancelled"})
            _jobs.pop(job_id, None)


def _run_pipeline_job(
    job_id: str,
    video_path: Path,
    srt_path: Path,
    target_lang: str | None,
    source_lang: str | None,
    engine: str,
    transcriber: WhisperTranscriber,
) -> None:
    """Sync function executed in a background thread for a single job."""
    job = _jobs[job_id]
    try:
        from gensubtitles.core.audio import audio_temp_context, extract_audio  # noqa: PLC0415
        from gensubtitles.core.srt_writer import write_srt  # noqa: PLC0415

        _set_progress("extracting", "[1/4] Extracting audio…", job=job)
        with audio_temp_context() as wav_path:
            extract_audio(video_path, wav_path)
            if job["cancel"].is_set():
                _cancel_job(job_id, video_path, srt_path)
                return

            _set_progress("transcribing", "[2/4] Transcribing…", job=job)
            transcription = transcriber.transcribe(wav_path, language=source_lang)

        if job["cancel"].is_set():
            _cancel_job(job_id, video_path, srt_path)
            return

        segments = transcription.segments
        detected_lang = transcription.language

        if target_lang is not None and target_lang != detected_lang:
            from gensubtitles.core.translator import translate_segments  # noqa: PLC0415

            _set_progress("translating", "[3/4] Translating…", job=job)

            def _on_seg_progress(current: int, total: int) -> None:
                _set_progress(
                    "translating",
                    f"[3/4] Translating {current}/{total}…",
                    current,
                    total,
                    job=job,
                )

            segments = translate_segments(
                segments,
                detected_lang,
                target_lang,
                progress_callback=_on_seg_progress,
                engine=engine,
            )
            if job["cancel"].is_set():
                _cancel_job(job_id, video_path, srt_path)
                return
        else:
            _set_progress("translating", "[3/4] Translation skipped", 0, 0, job=job)

        _set_progress("writing", "[4/4] Writing SRT…", job=job)
        write_srt(segments, srt_path)
        job["result"] = srt_path
        _set_progress("done", "✓ Done", 0, 0, job=job)

    except Exception as exc:  # noqa: BLE001
        label = (type(exc).__name__ + ": " + str(exc))[:200]
        srt_path.unlink(missing_ok=True)
        job["queue"].put({"stage": "error", "label": label})
        with _jobs_lock:
            _jobs.pop(job_id, None)
    finally:
        video_path.unlink(missing_ok=True)


@router.post("/subtitles/async")
def post_subtitles_async(
    file: UploadFile,
    target_lang: Optional[str] = Query(default=None, description="ISO 639-1 target language (e.g. 'es'). Omit to skip translation."),
    source_lang: Optional[str] = Query(default=None, description="Force source language (e.g. 'en'). Omit for auto-detect."),
    engine: str = Query(
        default="argos",
        description="Translation engine: argos (offline default), deepl, or libretranslate.",
        pattern="^(argos|deepl|libretranslate)$",
    ),
    transcriber: WhisperTranscriber = Depends(get_transcriber),
) -> dict:
    """Start subtitle generation asynchronously. Returns a job_id immediately."""
    video_suffix = Path(file.filename or "").suffix.lower()
    if video_suffix not in _SUPPORTED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported video format '{video_suffix}'. "
                f"Supported formats: {', '.join(sorted(_SUPPORTED_VIDEO_EXTENSIONS))}"
            ),
        )

    tmp_video = tempfile.NamedTemporaryFile(delete=False, suffix=video_suffix)
    try:
        shutil.copyfileobj(file.file, tmp_video)
    finally:
        tmp_video.flush()
        tmp_video.close()
        file.file.close()

    video_path = Path(tmp_video.name)

    tmp_srt = tempfile.NamedTemporaryFile(delete=False, suffix=".srt")
    tmp_srt.close()
    srt_path = Path(tmp_srt.name)

    job_id = str(uuid.uuid4())
    job: dict = {"queue": Queue(), "cancel": threading.Event(), "result": None, "error": None}
    with _jobs_lock:
        _jobs[job_id] = job

    threading.Thread(
        target=_run_pipeline_job,
        args=(job_id, video_path, srt_path, target_lang, source_lang, engine, transcriber),
        daemon=True,
    ).start()

    return {"job_id": job_id}


@router.get("/subtitles/{job_id}/stream")
async def stream_job_progress(job_id: str) -> StreamingResponse:
    """Server-Sent Events stream of progress events for a job."""
    with _jobs_lock:
        job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    q: Queue = job["queue"]
    loop = asyncio.get_running_loop()

    async def _event_generator():
        while True:
            event = await loop.run_in_executor(None, q.get)
            yield f"data: {json.dumps(event)}\n\n"
            if event.get("stage") in ("done", "error", "cancelled"):
                break

    return StreamingResponse(_event_generator(), media_type="text/event-stream")


@router.get("/subtitles/{job_id}/result")
def get_job_result(job_id: str, background_tasks: BackgroundTasks) -> FileResponse:
    """Fetch the completed SRT file for a finished job."""
    with _jobs_lock:
        job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    result_path: Path | None = job.get("result")
    if result_path is None:
        raise HTTPException(status_code=409, detail="Job not complete")

    def _cleanup() -> None:
        result_path.unlink(missing_ok=True)
        with _jobs_lock:
            _jobs.pop(job_id, None)

    background_tasks.add_task(_cleanup)
    return FileResponse(
        path=str(result_path),
        media_type="text/plain; charset=utf-8",
        filename="subtitles.srt",
    )


@router.delete("/subtitles/{job_id}")
def cancel_job(job_id: str) -> dict:
    """Signal cancellation for a running job."""
    with _jobs_lock:
        job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    job["cancel"].set()
    return {"status": "cancelling"}


@router.get("/languages")
def get_languages() -> dict:
    """
    Return all installed Argos Translate language pairs.

    Returns an empty list if no translation models are installed yet.
    """
    from gensubtitles.core.translator import list_installed_pairs  # noqa: PLC0415

    return {"pairs": list_installed_pairs()}
