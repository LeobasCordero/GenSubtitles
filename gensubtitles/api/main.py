"""
gensubtitles.api.main
~~~~~~~~~~~~~~~~~~~~~
FastAPI application entry point.

Startup: loads WhisperTranscriber (model weights) once via asynccontextmanager
lifespan and stores it on app.state.transcriber — accessed through
get_transcriber() dependency in dependencies.py.

Serve with:
    uvicorn gensubtitles.api.main:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from gensubtitles.core.transcriber import WhisperTranscriber
from gensubtitles.api.routers.subtitles import router as subtitles_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load WhisperTranscriber once at startup; release on shutdown."""
    model_size = os.environ.get("WHISPER_MODEL_SIZE", "small")
    device = os.environ.get("WHISPER_DEVICE", "auto")
    logger.info(
        "GenSubtitles API startup — loading WhisperTranscriber "
        "(model_size=%s device=%s)",
        model_size,
        device,
    )
    app.state.transcriber = WhisperTranscriber(model_size=model_size, device=device)
    logger.info("WhisperTranscriber ready — accepting requests")
    yield
    logger.info("GenSubtitles API shutdown — releasing transcriber")
    app.state.transcriber = None


app = FastAPI(
    title="GenSubtitles",
    description="Offline subtitle generation via faster-whisper + Argos Translate.",
    version="1.0.0",
    lifespan=lifespan,
)

_cors_origins_env = os.environ.get("CORS_ALLOW_ORIGINS", "")
_cors_origins: list[str] = (
    [o.strip() for o in _cors_origins_env.split(",") if o.strip()]
    if _cors_origins_env
    else ["http://localhost", "http://127.0.0.1"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── exception handlers ────────────────────────────────────────────────────────

@app.exception_handler(FileNotFoundError)
async def file_not_found_handler(request: Request, exc: FileNotFoundError) -> JSONResponse:
    """Map missing-file errors to HTTP 400 Bad Request."""
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Map value errors (e.g. unsupported file extension) to HTTP 400 Bad Request."""
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(EnvironmentError)
async def environment_error_handler(request: Request, exc: EnvironmentError) -> JSONResponse:
    """Map environment errors (e.g. FFmpeg missing) to HTTP 500 Internal Server Error."""
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.exception_handler(RuntimeError)
async def runtime_error_handler(request: Request, exc: RuntimeError) -> JSONResponse:
    """Map runtime failures (pipeline, transcription, etc.) to HTTP 500."""
    return JSONResponse(status_code=500, content={"detail": str(exc)})


# ── routers ───────────────────────────────────────────────────────────────────
app.include_router(subtitles_router)
