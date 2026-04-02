---
phase: 01-project-infrastructure
plan: 02
subsystem: infra
tags: [python, package-structure, typer, fastapi, ffmpeg]

requires:
  - phase: 01-project-infrastructure/01-01
    provides: pyproject.toml with deps, requirements.txt, .gitignore, placeholder dirs

provides:
  - Complete gensubtitles/ package skeleton (14 files)
  - Import-time FFmpeg check in gensubtitles/core/audio.py
  - Typer CLI stub with --input/--output options
  - FastAPI API stub directory with Phase 8 placeholders in dependencies.py
  - Root main.py as thin CLI shim

affects: [all subsequent phases build on this module structure]

tech-stack:
  added: [typer (CLI stub), fastapi (api stub)]
  patterns:
    - "Import-time environment check (shutil.which) raises EnvironmentError if FFmpeg absent"
    - "Root __init__.py contains only __version__ — no sub-package imports (avoids circular imports)"
    - "Root main.py is a thin shim delegating to CLI module"
    - "Every subdirectory has __init__.py including api/routers/"

key-files:
  created:
    - gensubtitles/__init__.py
    - gensubtitles/core/__init__.py
    - gensubtitles/core/audio.py
    - gensubtitles/core/transcriber.py
    - gensubtitles/core/translator.py
    - gensubtitles/core/srt_writer.py
    - gensubtitles/api/__init__.py
    - gensubtitles/api/main.py
    - gensubtitles/api/dependencies.py
    - gensubtitles/api/routers/__init__.py
    - gensubtitles/api/routers/subtitles.py
    - gensubtitles/cli/__init__.py
    - gensubtitles/cli/main.py
  modified:
    - main.py

key-decisions:
  - "gensubtitles/__init__.py has only __version__ = '0.1.0' — no sub-package imports to avoid circular import risk (D-12 anti-pattern)"
  - "gensubtitles/core/audio.py raises EnvironmentError at import time via shutil.which('ffmpeg') — fail fast before any pipeline runs (D-09/D-10/D-11)"
  - "api/dependencies.py stub created in Phase 1 to establish module location early, even though it is filled in Phase 8 (D-13)"
  - "root main.py replaced with thin shim: from gensubtitles.cli.main import app (D-14)"

patterns-established:
  - "Pattern: Import-time environment gate — check system deps at module load, raise EnvironmentError with cross-platform install hints"
  - "Pattern: Stub-first scaffolding — all future-phase files created as stubs now to prevent missing-module errors during development"

requirements-completed: [INF-02, INF-04]

duration: 10min
completed: 2026-04-02
---

# Phase 1 Plan 02: Package Skeleton Summary

**Full gensubtitles/ package tree created — 14 files establishing core/api/cli separation with import-time FFmpeg gate and CLI shim at root**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-04-02T00:00:00Z
- **Completed:** 2026-04-02T00:10:00Z
- **Tasks:** 2 completed
- **Files modified:** 14

## Accomplishments

- Created complete `gensubtitles/` package skeleton — all `__init__.py` stubs, core/api/cli modules at correct paths
- Implemented import-time FFmpeg check in `gensubtitles/core/audio.py` — raises `EnvironmentError` with OS-specific install hints if FFmpeg not on PATH
- Updated root `main.py` from old `def main()` to thin CLI shim; Typer stub in `gensubtitles/cli/main.py` provides `--input`/`--output` options

## Task Commits

1. **Task 1: Create package __init__.py stubs and core module stubs** — `6a45d4f` (feat)
2. **Task 2: Create API/CLI stubs and update root main.py** — `1ccd4b0` (feat)

## Files Created/Modified

- `gensubtitles/__init__.py` — `__version__ = "0.1.0"` only, no core imports
- `gensubtitles/core/__init__.py` — intentionally empty
- `gensubtitles/core/audio.py` — import-time FFmpeg check via `shutil.which`, raises `EnvironmentError`
- `gensubtitles/core/transcriber.py` — stub for Phase 3
- `gensubtitles/core/translator.py` — stub for Phase 4
- `gensubtitles/core/srt_writer.py` — stub for Phase 5
- `gensubtitles/api/__init__.py` — intentionally empty
- `gensubtitles/api/main.py` — stub for Phase 8
- `gensubtitles/api/dependencies.py` — Phase 8 placeholder with `whisper_model = None`, `argos_model = None`
- `gensubtitles/api/routers/__init__.py` — intentionally empty (prevents ModuleNotFoundError)
- `gensubtitles/api/routers/subtitles.py` — stub for Phase 8
- `gensubtitles/cli/__init__.py` — intentionally empty
- `gensubtitles/cli/main.py` — Typer stub with `--input`/`--output` CLI options
- `main.py` — replaced old `def main()` with thin CLI shim

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- All 14 files confirmed present on disk
- `python -c "import gensubtitles; print(gensubtitles.__version__)"` → `0.1.0`
- `shutil.which` check present in `gensubtitles/core/audio.py`
- `from gensubtitles.cli.main import app` present in `main.py`
- Task commits `6a45d4f` and `1ccd4b0` exist in git log
