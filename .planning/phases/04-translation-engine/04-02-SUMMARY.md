---
phase: 04-translation-engine
plan: 02
subsystem: testing
tags: [pytest, sys.modules, mocking, argostranslate, translator]

requires:
  - phase: 04-01
    provides: "gensubtitles/core/translator.py — all 5 public exports"
provides:
  - "tests/test_translator.py — 18 hermetic tests covering TRANS-01 through TRANS-05"
affects: [ci, regression]

tech-stack:
  added: []
  patterns:
    - "sys.modules injection for argostranslate mocking — same pattern as test_transcriber.py with faster_whisper"
    - "_inject_argostranslate() helper sets up fake module tree per test for isolation"
    - "caplog.at_level() for logging warning assertion"

key-files:
  created: [tests/test_translator.py]
  modified: []

key-decisions:
  - "Tests call _inject_argostranslate() per test (not fixture autouse) for explicit, readable setup"
  - "Deferred imports in translator.py means sys.modules mock must be set before calling the function, not before importing the module"
  - "Warning test needs pair absent initially so update_package_index is actually called"

patterns-established:
  - "sys.modules mocking for argostranslate: inject via _inject_argostranslate() helper before calling function under test"

requirements-completed: [TRANS-01, TRANS-02, TRANS-03, TRANS-04, TRANS-05]

duration: 10min
completed: 2026-04-03
---

# Phase 04-02: Translation Engine — Test Suite

**18 hermetic tests covering all TRANS-01 through TRANS-05 requirements using sys.modules mocking — zero real Argos Translate network calls, all pass in 0.30s.**

## Performance

- **Duration:** ~10 min
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Created `tests/test_translator.py` with 18 tests (all PASS)
- sys.modules injection pattern for argostranslate, consistent with transcriber test approach
- Fixed warning capture test to ensure `update_package_index` is actually called (pair must be absent initially)

## Task Commits

1. **Task 1: Write tests/test_translator.py** — `15181ed` (test)

## Files Created/Modified
- `tests/test_translator.py` — 18 hermetic tests: TRANS-01 (3 tests), TRANS-02 (2 tests), TRANS-03 (2 tests), TRANS-04 (4 tests), TRANS-05 (2 tests), offline/D-11 (3 tests), edge cases (2 tests)
