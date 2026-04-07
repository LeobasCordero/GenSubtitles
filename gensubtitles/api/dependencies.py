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

from fastapi import Request

from gensubtitles.core.transcriber import WhisperTranscriber


def get_transcriber(request: Request) -> WhisperTranscriber:
    """
    Return the WhisperTranscriber loaded by the lifespan context.

    The transcriber is stored on app.state.transcriber during startup and
    reused across all requests — no per-request model re-loading.
    """
    return request.app.state.transcriber
