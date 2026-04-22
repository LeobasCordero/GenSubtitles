---
plan: 12-02
phase: 12-retroactive-verification-pipeline-refactor
status: complete
completed: 2026-04-21
---

# Plan 12-02 Summary — Pipeline Refactor: transcriber= / cancel_event= + API Router Delegation

## What Was Built

### Task 1: Extended `run_pipeline()` with two new optional keyword params
- `transcriber=None` — accepts a pre-loaded `WhisperTranscriber` instance; falls back to creating one internally if None
- `cancel_event=None` — accepts a `threading.Event`; checks are inserted after audio extraction, after transcription, and after translation, raising `PipelineError("[cancelled]")` if set

**TDD cycle completed:**
- RED: 4 failing tests added (`test_transcriber_injection_uses_provided_transcriber`, `test_no_transcriber_creates_whisper_internally`, `test_cancel_event_set_before_call_raises_pipeline_error`, `test_cancel_event_set_during_audio_extraction_stops_before_transcription`, `test_cancel_event_none_runs_to_completion`)
- GREEN: `pipeline.py` modified; all 16 pipeline tests pass

### Task 2: Refactored `_run_pipeline_job()` to delegate to `run_pipeline()`
- Removed inline audio extraction, transcription, translation, and SRT write logic
- Added `from gensubtitles.core.pipeline import run_pipeline` top-level import
- Added `from gensubtitles.exceptions import PipelineError` top-level import
- New `_progress` callback maps `run_pipeline` labels to SSE stage/display strings
- `PipelineError("[cancelled]")` is caught and routes to `_cancel_job()`
- `job["result"] = Path(result.srt_path)` maintains Path type expected by GET /result

### Key Fix
- `WhisperTranscriber` import is now conditional (`if transcriber is None:`) to avoid ImportError when `faster_whisper` is not installed and a pre-loaded transcriber is injected
- `translate_segments` import is now conditional (`if target_lang is not None:`) to avoid ImportError when `argostranslate` is not installed and translation is skipped

## Key Files Modified

- `gensubtitles/core/pipeline.py` — added `import threading`, two new params, 3 cancel check points, conditional WhisperTranscriber/translate_segments imports
- `gensubtitles/api/routers/subtitles.py` — refactored `_run_pipeline_job()` to delegate to `run_pipeline()`; added PipelineError import
- `tests/test_pipeline.py` — 5 new tests (16 total, all pass); `FakeResult.duration` added to cancellation tests for compatibility
- `tests/test_api.py` — `FakeResult.duration` added for compatibility with `PipelineResult` construction

## Verification

All tests pass:
- `pytest tests/test_pipeline.py` — 16/16
- `pytest tests/test_api.py tests/test_api_steps.py` — 28/28
- `pytest tests/test_cli.py` — 20/20

## Issues

None (duration attribute on FakeResult needed adding in two test classes to match `PipelineResult` construction requirements).
