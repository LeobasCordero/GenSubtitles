"""
gensubtitles.api.dependencies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
FastAPI dependency callables for injecting shared state into route handlers.

Usage:
    from gensubtitles.api.dependencies import get_transcriber
    from fastapi import Depends

    @router.post("/subtitles")
    def post_subtitles(transcriber = Depends(get_transcriber)):
        ...
"""
from __future__ import annotations

from fastapi import HTTPException, Request

from gensubtitles.core.transcriber import WhisperTranscriber


def get_transcriber(request: Request) -> WhisperTranscriber:
    """
    Return the WhisperTranscriber loaded by the lifespan context.

    The transcriber is stored on app.state.transcriber during startup and
    reused across all requests — no per-request model re-loading.

    Raises:
        HTTPException(503): If the transcriber has not been loaded yet or has
            already been shut down (e.g., lifespan not started).
    """
    transcriber = request.app.state.transcriber
    if transcriber is None:
        raise HTTPException(
            status_code=503,
            detail="Transcriber is not available. The service may still be starting up.",
        )
    return transcriber
