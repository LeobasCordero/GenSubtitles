---
phase: 04-translation-engine
plan: 01
subsystem: core
tags: [argostranslate, tqdm, translation, namedtuple]

requires: []
provides:
  - "gensubtitles/core/translator.py — full offline translation module with 5 public exports"
  - "tqdm>=4.0.0 in requirements.txt and pyproject.toml"
affects: [pipeline, cli, api, srt-writer, tests]

tech-stack:
  added: [tqdm>=4.0.0]
  patterns:
    - "Deferred imports of argostranslate inside function bodies for lazy loading and test isolation"
    - "namedtuple for TranslatedSegment providing duck-typed .start/.end/.text for Phase 5 SRT writer"
    - "Best-effort network update with graceful fallback and warning log"

key-files:
  created: [gensubtitles/core/translator.py]
  modified: [requirements.txt, pyproject.toml]

key-decisions:
  - "All argostranslate imports deferred inside function bodies — consistent with transcriber.py's faster-whisper deferred import pattern, enables sys.modules mocking in tests"
  - "TranslatedSegment is a namedtuple (not dataclass) for duck-type compatibility with Phase 5 SRT writer"
  - "ensure_pair_installed uses tqdm.auto for cross-platform progress bar (D-10)"
  - "translate_segments same-lang short-circuit: returns list(segments) without any Argos calls (TRANS-02)"

patterns-established:
  - "Deferred argostranslate imports: import inside function body, not at module top"
  - "Best-effort network with warning fallback: try/except around update_package_index, log warning, continue"

requirements-completed: [TRANS-01, TRANS-02, TRANS-03, TRANS-04, TRANS-05]

duration: 10min
completed: 2026-04-03
---

# Phase 04-01: Translation Engine — Core Module

**Fully functional offline translation module using Argos Translate with tqdm download progress, same-language no-op, graceful offline fallback, and duck-typed TranslatedSegment output for Phase 5 SRT writer.**

## Performance

- **Duration:** ~10 min
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Implemented `gensubtitles/core/translator.py` with all 5 public exports
- Added `tqdm>=4.0.0` to both `requirements.txt` and `pyproject.toml`
- Established deferred-import pattern for argostranslate (enables sys.modules mocking in tests)

## Task Commits

1. **Task 1: Add tqdm dependency** - part of `6f7f3b8` (feat)
2. **Task 2: Implement translator.py** - part of `6f7f3b8` (feat)

## Files Created/Modified
- `gensubtitles/core/translator.py` — Full offline translation module (TranslatedSegment, translate_segments, ensure_pair_installed, is_pair_available, list_installed_pairs)
- `requirements.txt` — Added `tqdm>=4.0.0`
- `pyproject.toml` — Added `tqdm>=4.0.0` to project dependencies
