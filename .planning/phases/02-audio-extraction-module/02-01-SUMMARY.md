---
plan: 02-01
phase: 02-audio-extraction-module
status: complete
completed: 2026-04-02
commit: 4fb4017
---

## Summary

Created the shared exception hierarchy and pytest fixture infrastructure required by all subsequent Phase 2 plans.

## What Was Built

- `gensubtitles/exceptions.py` — `GenSubtitlesError` base class + `AudioExtractionError` subclass
- `tests/conftest.py` — Two session-scoped fixtures: `synthetic_video` (video+audio, lavfi) and `silent_video` (video-only, -an flag)

## Key Files Created

- `gensubtitles/exceptions.py`
- `tests/conftest.py`

## Verification

- `from gensubtitles.exceptions import GenSubtitlesError, AudioExtractionError` ✓
- `AudioExtractionError` is subclass of `GenSubtitlesError` ✓
- `pytest --collect-only` exits 0, 4 tests collected ✓
- `tests/test_infrastructure.py` 4/4 passed ✓

## Decisions

- Extended `RuntimeError` for `GenSubtitlesError` to match the shipped implementation and satisfy D-01
- `scope="session"` on both fixtures — FFmpeg runs once per pytest invocation
- `tmp_path_factory` used (not `tmp_path`) for session-scoped temp dirs

## Requirements Addressed

- AUD-01, AUD-02, AUD-03, AUD-04 (infrastructure prerequisites)
