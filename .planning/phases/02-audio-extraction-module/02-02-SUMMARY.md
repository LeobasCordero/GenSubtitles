---
plan: 02-02
phase: 02-audio-extraction-module
status: complete
completed: 2026-04-02
commit: e7bce33
---

## Summary

Replaced the Phase 1 stub in `gensubtitles/core/audio.py` with full implementation: `extract_audio()` and `audio_temp_context()`.

## What Was Built

- `extract_audio(video_path, output_path)` — validates extension, runs FFmpeg at 16kHz mono WAV, raises `AudioExtractionError` on FFmpeg failure
- `audio_temp_context(suffix=".wav")` — `@contextmanager` that creates temp file via `mkstemp`, yields Path, deletes on exit via `finally` block
- `SUPPORTED_EXTENSIONS` frozenset: `{".mp4", ".mkv", ".avi", ".mov", ".webm"}`
- Import-time FFmpeg check preserved from Phase 1 stub

## Key Files Modified

- `gensubtitles/core/audio.py` (replaced stub)

## Design Notes

- `os.close(fd)` immediately after `mkstemp` — required on Windows so FFmpeg can write to the path
- `subprocess.run(..., check=False)` + manual returncode check — gives us full stderr in the exception message
- `tmp_path.unlink(missing_ok=True)` in `finally` — handles case where block raises before writing

## Verification

- `from gensubtitles.core.audio import extract_audio, audio_temp_context, SUPPORTED_EXTENSIONS` ✓
- Import-time EnvironmentError raised when FFmpeg absent ✓
- `tests/test_infrastructure.py` 4/4 passed ✓
- Note: `tests/test_audio.py` (Plan 03) will perform functional validation once FFmpeg is available

## Requirements Addressed

- AUD-01: extension validation
- AUD-02: FFmpeg subprocess, 16kHz mono WAV
- AUD-03: AudioExtractionError on non-zero exit / no audio stream
- AUD-04: audio_temp_context cleanup
