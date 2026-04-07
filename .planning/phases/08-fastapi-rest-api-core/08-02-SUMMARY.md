---
plan: 08-02
phase: 08-fastapi-rest-api-core
status: complete
completed: 2026-04-07
commit: 26a8475
---

## Summary

Implemented the POST /subtitles endpoint and wired the router into the FastAPI app.

## What Was Built

- `gensubtitles/api/routers/subtitles.py` — Full POST /subtitles implementation:
  - `def post_subtitles(...)` (sync def — FastAPI routes to thread pool, API-03)
  - UploadFile copied to `NamedTemporaryFile` on disk before FFmpeg invocation (API-02)
  - Uses preloaded `WhisperTranscriber` via `Depends(get_transcriber)` (API-04)
  - `BackgroundTasks` deletes both temp files (video + SRT) after response (UAT-6)
  - Query params: `model_size`, `target_lang`, `source_lang`
  - `FileResponse` with `media_type="text/plain; charset=utf-8"` and `filename="subtitles.srt"`
- `gensubtitles/api/main.py` — Added router import and `app.include_router(subtitles_router)`

## Key Files

key-files:
  created:
    - gensubtitles/api/routers/subtitles.py
  modified:
    - gensubtitles/api/main.py

## Decisions

- Audio, srt_writer imports are **lazy** (inside function body) to avoid import-time FFmpeg check from audio.py — enables testing without FFmpeg installed
- Translator import remains lazy (inside `if target_lang` block) — avoids argostranslate side effects
- `run_pipeline()` NOT used — would create new WhisperTranscriber internally, defeating API-04

## Verification

- `python -c "from gensubtitles.api.main import app; routes = [r.path for r in app.routes]; assert '/subtitles' in routes"` → passes ✓
- Route is `def` (not `async def`) — confirmed in source ✓
- `shutil.copyfileobj` used for UploadFile → NamedTemporaryFile copy ✓
- Two `background_tasks.add_task(path.unlink, missing_ok=True)` calls ✓

## Requirements Addressed

- API-01: POST /subtitles endpoint accepting multipart video upload
- API-02: UploadFile copied to NamedTemporaryFile before FFmpeg
- API-03: sync def route — auto thread pool via FastAPI
