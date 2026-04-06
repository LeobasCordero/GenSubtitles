---
plan: 06-02
phase: 06-core-pipeline-assembly
status: complete
completed_at: 2026-04-06
commit: 2a9ce23
---

# Plan 06-02: Implement pipeline.py via TDD — COMPLETE

## What Was Built

`gensubtitles/core/pipeline.py` — the central wiring point of the application.
Implements `PipelineResult` dataclass and `run_pipeline()` function using
test-driven development: 8 failing tests written first, then implementation
made them pass.

## Key Files

| File | Role |
|------|------|
| `gensubtitles/core/pipeline.py` | `PipelineResult` dataclass + `run_pipeline()` |
| `tests/test_pipeline.py` | 8 tests covering all UAT criteria |

## Implementation Details

### PipelineResult (dataclass)
Fields: `srt_path: str`, `detected_language: str`, `segment_count: int`,
`audio_duration_seconds: float`

### run_pipeline() — 4 stages
1. **Extracting audio** (stage 1/4) — `extract_audio()` via `audio_temp_context`
2. **Transcribing** (stage 2/4) — `WhisperTranscriber.transcribe()`
3. **Translating / Translation skipped** (stage 3/4) — conditional on `target_lang`
4. **Writing SRT** (stage 4/4) — `write_srt()`

All lazy imports (audio, srt_writer, transcriber, translator) to prevent
`EnvironmentError` in import-only environments (no FFmpeg, no GPU).

## Test Strategy

`sys.modules` injection pattern (same as transcriber tests) to run without
FFmpeg, GPU, or model downloads. Each test injects fake module objects that
expose the mocked functions.

## Verification

- `python -m pytest tests/test_pipeline.py -v` — 8/8 passed
- `python -m pytest tests/test_transcriber.py` — 25/25 passed (regression clean)
- `from gensubtitles.core.pipeline import run_pipeline, PipelineResult` — imports OK
- `PipelineResult` fields are `['srt_path', 'detected_language', 'segment_count', 'audio_duration_seconds']`

## Self-Check: PASSED
