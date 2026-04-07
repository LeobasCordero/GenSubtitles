---
plan: 08-03
phase: 08-fastapi-rest-api-core
status: complete
completed: 2026-04-07
commit: 098e2a2
---

## Summary

Wrote the Phase 8 test suite — 8 tests covering all UAT acceptance criteria for the FastAPI REST API.

## What Was Built

- `tests/test_api.py` — 8 tests across 2 classes:
  - `TestPostSubtitles` (7 tests): API-01 through API-03, UAT 5 & 6
  - `TestLifespan` (1 test): API-04

## Test Coverage

| Test | Requirement | What It Verifies |
|------|------------|-----------------|
| test_valid_upload_returns_200_and_srt | API-01 | 200 response, SRT body with `-->` |
| test_no_target_lang_skips_translation | API-01 | translate_segments NOT called without target_lang |
| test_model_size_query_param_passed_to_transcriber | API-01 | transcriber.transcribe called (preloaded model used) |
| test_upload_file_copied_to_disk_before_extract | API-02 | Video path passed to extract_audio ends with .mp4 |
| test_temp_files_deleted_after_response | UAT-6 | Both temp files (video + SRT) deleted after response |
| test_invalid_file_returns_error_json | UAT-5 | RuntimeError returns JSON `{"detail": "..."}` not 500 trace |
| test_target_lang_triggers_translation | API-01 | translate_segments IS called when target_lang set |
| test_lifespan_sets_transcriber_on_app_state | API-04 | WhisperTranscriber loaded once, stored on app.state |

## Key Files

key-files:
  created:
    - tests/test_api.py

## Decisions

- Used `sys.modules` injection for `gensubtitles.core.audio` and `gensubtitles.core.srt_writer` to bypass import-time FFmpeg check (EnvironmentError in audio.py) — no FFmpeg required to run tests
- All router imports are lazy (inside function body) enabling this mock injection pattern
- `TestClient(app)` with `dependency_overrides[get_transcriber]` for transcriber mocking

## Verification

- `python -m pytest tests/test_api.py -x 2>&1 | Write-Output` → `8 passed in 2.25s` ✓
- No FFmpeg, GPU, or network access required ✓

## Requirements Addressed

- API-01: POST /subtitles endpoint — upload, response, query params
- API-02: UploadFile → NamedTemporaryFile copy before FFmpeg
- API-03: Sync def auto thread pool (event loop not blocked)
- API-04: Model loaded once at startup, accessible to all requests
