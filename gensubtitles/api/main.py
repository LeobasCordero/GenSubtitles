"""
gensubtitles.api.main
~~~~~~~~~~~~~~~~~~~~~
FastAPI application entry point.

Startup: loads WhisperTranscriber (model weights) in a background thread so
the server starts accepting connections immediately.  Poll GET /status to track
loading progress; GET /languages is also available immediately.

Serve with:
    uvicorn gensubtitles.api.main:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import logging
import os
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from gensubtitles.core.transcriber import WhisperTranscriber
from gensubtitles.api.routers.steps import router as steps_router
from gensubtitles.api.routers.subtitles import router as subtitles_router

logger = logging.getLogger(__name__)

# ── startup state (updated by background loader thread) ───────────────────────
_startup_state: dict = {
    "stage": "starting",       # starting | downloading | loading | ready | error
    "message": "Starting server\u2026",
    "progress": -1,            # -1 = indeterminate, 0-100 = determinate percentage
}
_startup_lock = threading.Lock()


def _set_startup(stage: str, message: str, progress: int = -1) -> None:
    with _startup_lock:
        _startup_state["stage"] = stage
        _startup_state["message"] = message
        _startup_state["progress"] = progress


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start model loading in a background thread; yield immediately so routes are reachable."""
    # Reset startup state for this lifespan cycle (avoids stale state from prior runs)
    _set_startup("starting", "Starting server\u2026", -1)

    model_size = os.environ.get("WHISPER_MODEL_SIZE", "medium")
    device = os.environ.get("WHISPER_DEVICE", "auto")
    skip_prefetch = os.environ.get("GENSUBTITLES_SKIP_HF_PREFETCH", "").lower() in ("1", "true", "yes")

    def _load() -> None:
        if not skip_prefetch:
            _download_model_if_needed(model_size)

        # If download phase set an error, bail out
        with _startup_lock:
            if _startup_state["stage"] == "error":
                return

        # ── Load model into memory (indeterminate) ─────────────────────────
        _set_startup("loading", f"Loading '{model_size}' model into memory\u2026", -1)
        logger.info("Loading WhisperTranscriber (model_size=%s device=%s)", model_size, device)
        try:
            app.state.transcriber = WhisperTranscriber(model_size=model_size, device=device)
            _set_startup("ready", "Ready", 100)
            logger.info("WhisperTranscriber ready")
        except Exception as exc:  # noqa: BLE001
            _set_startup("error", f"Model failed to load: {exc}", -1)
            logger.error("WhisperTranscriber failed: %s", exc)

    app.state.transcriber = None
    threading.Thread(target=_load, daemon=True).start()
    yield
    app.state.transcriber = None
    _set_startup("stopped", "Server stopped.", -1)


def _download_model_if_needed(model_size: str) -> None:
    """Download Whisper model from HuggingFace Hub if not already cached.

    Separated from lifespan so it can be skipped in tests via
    ``GENSUBTITLES_SKIP_HF_PREFETCH=1``.
    """
    import huggingface_hub
    import huggingface_hub.file_download as _hfd

    repo_id = f"Systran/faster-whisper-{model_size}"

    # Check local cache first
    already_cached = False
    try:
        huggingface_hub.snapshot_download(repo_id, local_files_only=True)
        already_cached = True
    except Exception:  # noqa: BLE001
        pass

    if already_cached:
        return

    # Try to get total byte count for percentage display
    total_bytes = 0
    try:
        api = huggingface_hub.HfApi()
        tree = list(api.list_repo_tree(repo_id, repo_type="model", recursive=True))
        total_bytes = sum(getattr(f, "size", 0) or 0 for f in tree)
    except Exception:  # noqa: BLE001
        pass

    _downloaded: list[int] = [0]
    _dl_lock = threading.Lock()
    _orig_tqdm = _hfd.tqdm

    class _ByteTqdm(_orig_tqdm):  # type: ignore[misc]
        def update(self, n: int = 1) -> None:
            super().update(n)
            n = n or 0
            if n > 0:
                with _dl_lock:
                    _downloaded[0] += n
                    mb = _downloaded[0] / 1_048_576
                    if total_bytes > 0:
                        pct = min(int(_downloaded[0] / total_bytes * 100), 99)
                        total_mb = total_bytes / 1_048_576
                        _set_startup(
                            "downloading",
                            f"\u23ec Downloading '{model_size}' model (first time only)\u2026 {pct}% ({mb:.0f}\u202fMB / {total_mb:.0f}\u202fMB)",
                            pct,
                        )
                    else:
                        _set_startup(
                            "downloading",
                            f"\u23ec Downloading '{model_size}' model (first time only)\u2026 {mb:.0f}\u202fMB downloaded",
                            -1,
                        )

    initial_progress = 0 if total_bytes > 0 else -1
    _set_startup(
        "downloading",
        f"\u23ec Downloading '{model_size}' model (first time only)\u2026",
        initial_progress,
    )
    _hfd.tqdm = _ByteTqdm
    try:
        huggingface_hub.snapshot_download(repo_id)
    except Exception as exc:  # noqa: BLE001
        _set_startup("error", f"Model download failed: {exc}", -1)
        logger.error("Model download failed: %s", exc)
    finally:
        _hfd.tqdm = _orig_tqdm


app = FastAPI(
    title="GenSubtitles",
    description="Offline subtitle generation via faster-whisper + Argos Translate.",
    version="1.0.0",
    lifespan=lifespan,
)

_cors_origins_env = os.environ.get("CORS_ALLOW_ORIGINS", "")
_cors_origins: list[str] = (
    [o.strip() for o in _cors_origins_env.split(",") if o.strip()]
    if _cors_origins_env.strip()
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
app.include_router(steps_router)


# ── status endpoint ───────────────────────────────────────────────────────────

@app.get("/status")
def get_status() -> dict:
    """Return current server startup state. Available immediately on first connection."""
    with _startup_lock:
        return dict(_startup_state)
