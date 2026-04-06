---
plan: 06-01
phase: 06-core-pipeline-assembly
status: complete
completed_at: 2026-04-06
commit: 29d1fb2
---

# Plan 06-01: Extend TranscriptionResult + PipelineError — COMPLETE

## What Was Built

Extended `TranscriptionResult` namedtuple with a third field `duration` (float seconds) and
added `PipelineError` to the shared exceptions module so `pipeline.py` (Plan 02) can import it.

## Key Changes

### gensubtitles/core/transcriber.py
- `TranscriptionResult` namedtuple now declares `["segments", "language", "duration"]`
- `WhisperTranscriber.transcribe()` returns `TranscriptionResult(..., duration=info.duration)`

### gensubtitles/exceptions.py
- `PipelineError(GenSubtitlesError)` added — raised by `run_pipeline()` on stage failures

### tests/test_transcriber.py
- `_make_transcription_info` stub updated to include `duration=120.0`

## Verification

- All 25 existing transcriber tests pass with the updated duration field
- `TranscriptionResult` has three fields: `segments`, `language`, `duration`
- `PipelineError` is a subclass of `GenSubtitlesError`

## Key Files

| File | Role |
|------|------|
| `gensubtitles/core/transcriber.py` | Extended namedtuple + construction site |
| `gensubtitles/exceptions.py` | New PipelineError class |
| `tests/test_transcriber.py` | Updated test stub |

## Self-Check: PASSED
