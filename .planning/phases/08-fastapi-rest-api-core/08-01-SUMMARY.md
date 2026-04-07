---
plan: 08-01
phase: 08-fastapi-rest-api-core
status: complete
completed: 2026-04-07
commit: f33ff0a
---

## Summary

Implemented the FastAPI application foundation for Phase 8.

## What Was Built

- `gensubtitles/api/main.py` — FastAPI app instance with:
  - `lifespan` asynccontextmanager that loads `WhisperTranscriber` once at startup (reads `WHISPER_MODEL_SIZE` and `WHISPER_DEVICE` env vars) and stores it on `app.state.transcriber`
  - `@app.exception_handler(FileNotFoundError)` → HTTP 400 JSON `{"detail": "..."}`
  - `@app.exception_handler(RuntimeError)` → HTTP 500 JSON `{"detail": "..."}`
- `gensubtitles/api/dependencies.py` — `get_transcriber(request: Request) -> WhisperTranscriber` dependency that reads and returns `request.app.state.transcriber`

## Key Files

key-files:
  created:
    - gensubtitles/api/main.py
    - gensubtitles/api/dependencies.py

## Decisions

- `WhisperTranscriber` stored on `app.state.transcriber` (not a module-level singleton) for clean lifespan management and testability via `dependency_overrides`
- `RuntimeError` exception handler intentionally catches `GenSubtitlesError` hierarchy (inherits from `RuntimeError`)
- Router import deferred to Plan 08-02 to maintain clean dependency boundaries

## Verification

- `python -c "from gensubtitles.api.main import app; print(app.title)"` → `GenSubtitles` ✓
- `python -c "from gensubtitles.api.dependencies import get_transcriber; print('ok')"` → `ok` ✓
- Both exception handlers registered in `app.exception_handlers`

## Requirements Addressed

- API-04: Models loaded exactly once at startup via lifespan, accessible across all requests
