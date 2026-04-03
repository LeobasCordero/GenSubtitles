---
phase: 02
slug: audio-extraction-module
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-02
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `python -m pytest tests/test_audio.py -v` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~10–30 seconds (FFmpeg fixture generated once per session) |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_audio.py -v`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 02-01-T1 | 01 | 1 | AUD-01..04 | unit | `pytest tests/test_audio.py -v` | ⬜ pending |
| 02-02-T1 | 02 | 1 | AUD-01..04 | unit | `pytest tests/test_audio.py -v` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/conftest.py` — session-scoped synthetic video fixture (FFmpeg lavfi, 1-second, 440Hz sine)
- [ ] `tests/test_audio.py` — stubs/shells for AUD-01, AUD-02, AUD-03, AUD-04

*Existing `tests/test_infrastructure.py` and `pyproject.toml` pytest config already in place from Phase 1.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| FFmpeg not on PATH → EnvironmentError at import | INF-04 / D-05 | Requires system-level FFmpeg removal | Temporarily rename ffmpeg binary; `python -c "import gensubtitles.core.audio"` |

---

## Acceptance Criteria Summary

All of the following must be true before Phase 2 is considered complete:

- [ ] `gensubtitles/exceptions.py` exists with `GenSubtitlesError` and `AudioExtractionError`
- [ ] `gensubtitles/core/audio.py` has `extract_audio(video_path, output_path)` and `audio_temp_context()`
- [ ] `tests/conftest.py` has `synthetic_video` session-scoped fixture
- [ ] `python -m pytest tests/test_audio.py -v` exits 0 (all tests green)
- [ ] `python -m pytest tests/ -v` exits 0 (no regressions to Phase 1 tests)
- [ ] AUD-01: Unsupported extension raises `ValueError` before FFmpeg spawn
- [ ] AUD-02: Output WAV has framerate=16000 and nchannels=1 (verified by `wave.open()`)
- [ ] AUD-03: Video with no audio stream raises `AudioExtractionError`
- [ ] AUD-04: `audio_temp_context()` deletes temp file on both success and exception
