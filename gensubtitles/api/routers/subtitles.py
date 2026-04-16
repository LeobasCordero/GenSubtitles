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


# ── stateless upload/download step endpoints ──────────────────────────────────

@router.post("/subtitles/extract", summary="Step 1: Extract audio from video")
async def post_subtitles_extract(
    video: UploadFile,
    background_tasks: BackgroundTasks,
) -> FileResponse:
    """Upload a video file; receive the extracted 16kHz mono WAV as a file download.

    Stateless — no server-side state retained.
    """
    from gensubtitles.core.steps import AUDIO_FILENAME, extract_audio_step, sanitize_stem  # noqa: PLC0415

    suffix = Path(video.filename or "upload").suffix.lower() or ".mp4"
    original_stem = sanitize_stem(Path(video.filename or "").stem)
    download_name = f"{original_stem}.wav" if original_stem else AUDIO_FILENAME
    _tmp_video = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp_video = Path(_tmp_video.name)
    tmp_work = Path(tempfile.mkdtemp())
    try:
        shutil.copyfileobj(video.file, _tmp_video)
        _tmp_video.flush()
        wav_path = extract_audio_step(tmp_video, tmp_work)
    except Exception as exc:  # noqa: BLE001
        shutil.rmtree(tmp_work, ignore_errors=True)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        video.file.close()
        _tmp_video.close()
        tmp_video.unlink(missing_ok=True)

    background_tasks.add_task(shutil.rmtree, tmp_work, True)
    return FileResponse(wav_path, media_type="audio/wav", filename=download_name)


@router.post("/subtitles/transcribe", summary="Step 2: Transcribe audio to segments JSON")
async def post_subtitles_transcribe(
    audio: UploadFile,
    background_tasks: BackgroundTasks,
    source_lang: Optional[str] = Query(None, description="Force source language (ISO 639-1). Omit for auto-detect."),
    model_size: str = Query("medium", description="Whisper model size."),
    transcriber: WhisperTranscriber = Depends(get_transcriber),
) -> FileResponse:
    """Upload a WAV file; receive transcription.json (segments with detected language).

    Stateless. Uses the pre-loaded WhisperTranscriber from server lifespan.
    """
    from gensubtitles.core.steps import transcribe_step  # noqa: PLC0415

    tmp_work = Path(tempfile.mkdtemp())
    wav_path = tmp_work / "audio.wav"
    try:
        with wav_path.open("wb") as f:
            shutil.copyfileobj(audio.file, f)
        transcribe_step(
            tmp_work,
            transcriber=transcriber,
            model_size=model_size,
            source_lang=source_lang or None,
        )
    except Exception as exc:  # noqa: BLE001
        shutil.rmtree(tmp_work, ignore_errors=True)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        audio.file.close()

    json_path = tmp_work / "transcription.json"
    background_tasks.add_task(shutil.rmtree, tmp_work, True)
    return FileResponse(json_path, media_type="application/json", filename="transcription.json")


@router.post("/subtitles/translate", summary="Step 3: Translate segments JSON")
async def post_subtitles_translate(
    segments: UploadFile,
    background_tasks: BackgroundTasks,
    target_lang: str = Query(..., description="Target ISO 639-1 language code (e.g. 'es')."),
    engine: str = Query("argos", description="Translation engine: argos / deepl / libretranslate."),
) -> FileResponse:
    """Upload transcription.json; receive translation.json.

    Stateless. Input file is used as transcription.json regardless of filename.
    """
    from gensubtitles.core.steps import translate_step  # noqa: PLC0415

    tmp_work = Path(tempfile.mkdtemp())
    trans_path = tmp_work / "transcription.json"
    try:
        with trans_path.open("wb") as f:
            shutil.copyfileobj(segments.file, f)
        translate_step(tmp_work, target_lang=target_lang, engine=engine)
    except Exception as exc:  # noqa: BLE001
        shutil.rmtree(tmp_work, ignore_errors=True)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        segments.file.close()

    out_path = tmp_work / "translation.json"
    background_tasks.add_task(shutil.rmtree, tmp_work, True)
    return FileResponse(out_path, media_type="application/json", filename="translation.json")


@router.post("/subtitles/write", summary="Step 4: Write SRT from segments JSON")
async def post_subtitles_write(
    segments: UploadFile,
    background_tasks: BackgroundTasks,
) -> FileResponse:
    """Upload transcription.json or translation.json; receive subtitles.srt.

    Stateless. Input treated as a flat segments JSON list [{start,end,text}].
    """
    from gensubtitles.core.steps import write_srt_step  # noqa: PLC0415

    tmp_work = Path(tempfile.mkdtemp())
    # Save as translation.json so write_srt_step prefers it (flat list format)
    seg_path = tmp_work / "translation.json"
    srt_out = tmp_work / "subtitles.srt"
    try:
        with seg_path.open("wb") as f:
            shutil.copyfileobj(segments.file, f)
        write_srt_step(tmp_work, srt_out)
    except Exception as exc:  # noqa: BLE001
        shutil.rmtree(tmp_work, ignore_errors=True)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        segments.file.close()

    background_tasks.add_task(shutil.rmtree, tmp_work, True)
    return FileResponse(srt_out, media_type="text/plain", filename="subtitles.srt")
