"""
gensubtitles.api.routers.steps
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Path-based step endpoints for the desktop GUI.

Because the GUI and the FastAPI server run on the same machine, these
endpoints accept local file *paths* rather than file uploads, eliminating
unnecessary in-memory I/O for large video files.

Routes:
    POST /steps/extract    — {video_path, work_dir} → {status, output_path}
    POST /steps/transcribe — {work_dir, ...}        → {status, output_path}
    POST /steps/translate  — {work_dir, target_lang} → {status, output_path}
    POST /steps/write      — {work_dir, output_path} → {status, output_path}
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from gensubtitles.api.dependencies import get_transcriber
from gensubtitles.core.transcriber import WhisperTranscriber

router = APIRouter(tags=["steps"])

_LOOPBACK_HOSTS = {"127.0.0.1", "::1"}


def _require_loopback(request: Request) -> None:
    """Raise 403 if the request did not originate from the loopback interface."""
    host = request.client.host if request.client else None
    if host not in _LOOPBACK_HOSTS:
        raise HTTPException(
            status_code=403,
            detail="This endpoint is only available to local clients.",
        )


# ── request/response models ───────────────────────────────────────────────────

class ExtractRequest(BaseModel):
    video_path: str
    work_dir: str


class TranscribeRequest(BaseModel):
    work_dir: str
    model_size: str = "medium"
    source_lang: Optional[str] = None
    device: str = "auto"


class TranslateRequest(BaseModel):
    work_dir: str
    target_lang: str
    engine: str = "argos"


class WriteRequest(BaseModel):
    work_dir: str
    output_path: str


class StepResponse(BaseModel):
    status: str
    output_path: str


# ── route handlers ────────────────────────────────────────────────────────────

@router.post("/steps/extract", response_model=StepResponse, summary="Step 1 (local path): Extract audio")
def post_steps_extract(req: ExtractRequest, request: Request) -> StepResponse:
    """Extract audio from a locally accessible video file.

    Writes audio.wav to req.work_dir. Returns the path to the written file.
    """
    _require_loopback(request)
    from gensubtitles.core.steps import extract_audio_step  # noqa: PLC0415

    try:
        out = extract_audio_step(req.video_path, req.work_dir)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return StepResponse(status="done", output_path=str(out))


@router.post("/steps/transcribe", response_model=StepResponse, summary="Step 2 (local path): Transcribe audio")
def post_steps_transcribe(
    req: TranscribeRequest,
    request: Request,
    transcriber: WhisperTranscriber = Depends(get_transcriber),
) -> StepResponse:
    """Transcribe audio.wav from work_dir. Writes transcription.json.

    Uses the pre-loaded WhisperTranscriber from server lifespan — no model reload.
    """
    _require_loopback(request)
    from gensubtitles.core.steps import TRANSCRIPTION_FILENAME, transcribe_step  # noqa: PLC0415

    try:
        transcribe_step(
            req.work_dir,
            transcriber=transcriber,
            model_size=req.model_size,
            source_lang=req.source_lang,
            device=req.device,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    out = Path(req.work_dir) / TRANSCRIPTION_FILENAME
    return StepResponse(status="done", output_path=str(out))


@router.post("/steps/translate", response_model=StepResponse, summary="Step 3 (local path): Translate segments")
def post_steps_translate(req: TranslateRequest, request: Request) -> StepResponse:
    """Translate transcription.json in work_dir. Writes translation.json."""
    _require_loopback(request)
    from gensubtitles.core.steps import TRANSLATION_FILENAME, translate_step  # noqa: PLC0415

    try:
        translate_step(req.work_dir, target_lang=req.target_lang, engine=req.engine)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    out = Path(req.work_dir) / TRANSLATION_FILENAME
    return StepResponse(status="done", output_path=str(out))


@router.post("/steps/write", response_model=StepResponse, summary="Step 4 (local path): Write SRT")
def post_steps_write(req: WriteRequest, request: Request) -> StepResponse:
    """Write SRT from translation.json (or transcription.json) in work_dir."""
    _require_loopback(request)
    from gensubtitles.core.steps import write_srt_step  # noqa: PLC0415

    try:
        out = write_srt_step(req.work_dir, req.output_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return StepResponse(status="done", output_path=str(out))
