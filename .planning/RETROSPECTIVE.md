# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

---

## Milestone: v1.0 — GenSubtitles MVP

**Shipped:** 2026-04-10  
**Phases:** 16 | **Plans:** 30 | **Timeline:** 8 days (2026-04-02 → 2026-04-10)

### What Was Built

- Full offline subtitle pipeline: Video → FFmpeg (16kHz WAV) → faster-whisper → Argos Translate → SRT
- FastAPI REST API with `POST /subtitles`, `GET /languages`, Uvicorn serve, OpenAPI docs at `/docs`
- Typer CLI with `--input`, `--output`, `--model`, `--target-lang`, progress output, and exit codes
- CustomTkinter desktop GUI (`gensubtitles gui`) — Full generate workflow, stage progress, elapsed timer (HH:MM:SS), reactive Clear button, field disable during pipeline, mandatory field markers, target-language dropdown
- 73-test suite with full mock coverage (audio, transcription, translation, SRT, pipeline, CLI, API)
- Bilingual README (English + Spanish) with install, CLI usage, and API usage docs

### What Worked

- **Vertical slicing** — each phase delivered a working feature end-to-end; no phase left dangling stubs
- **Decimal phase numbering** (999.x) — clean way to add backlog GUI features after main phases without renumbering
- **Deferred imports pattern** — guarded all heavy imports (`requests`, `tkinter`) inside method bodies; unit tests run fast without full dep load
- **Mock-first testing** — mocking FFmpeg/Whisper/Argos at boundaries gave a fast, hermetic test suite (2.87s for 73 tests)
- **Single PLAN.md per small feature** — GUI polish backlog phases (999.2–999.9) were quick to plan and execute with 1-plan phases

### What Was Inefficient

- **PROJECT.md fell behind** — Active requirements section remained stale (shipped items stayed in Active, not Validated) until milestone completion; should be updated as phases complete
- **Nyquist validation was skipped** — No `VALIDATION.md` files were written for any phase; the audit caught this as a documentation gap but all functionality was verified through the test suite
- **GUI testing is fully manual** — No automated tests for `gensubtitles/gui/main.py`; all verification required launching the GUI or syntax-checking only
- **Human E2E test deferred** — `POST /subtitles` with real models requires Argos + faster-whisper installed and was never formally verified end-to-end

### Patterns Established

- `self.after(0, callback)` for Tk thread-safety — always marshal API thread results back to Tk main thread via `after`
- Deferred imports (`from tkinter import ...` inside method bodies) — used across GUI and CLI to prevent headless DISPLAY errors
- `threading.Thread(daemon=True)` for all long-running operations in the GUI — avoids blocking window close
- FastAPI sync `def` for CPU-bound routes — gets automatic thread pool without event loop blocking
- `list(segments)` to materialize faster-whisper lazy generator before returning
- Decimal phase prefix for backlog features (999.x) — avoids milestone renumbering while keeping ordering clear

### Key Lessons

1. **Keep PROJECT.md current during execution** — updating requirements from Active → Validated as each phase ships eliminates end-of-milestone cleanup work
2. **GUI needs a testing strategy** — even smoke tests (launch, interact, close) would catch regressions; consider `pytest-tkinter` or screenshot diffing in v2.0
3. **Nyquist VALIDATION.md is worth writing** — even a brief checklist per phase reduces audit debt at milestone close
4. **Backlog phase naming** — 999.x works well for features discovered during execution; record them via `/gsd-add-backlog` immediately when identified

### Cost Observations

- Model mix: sonnet for execution (all phases), opus for planning
- Sessions: ~8 day timeline with multiple sessions per day
- Notable: Small 1-plan phases (999.x GUI features) executed very efficiently — low context cost, high output

---

---

## Milestone: v1.0 — GenSubtitles MVP (Backlog Expansion)

**Shipped:** 2026-04-22  
**Phases:** 40 total (13 core + 27 backlog 999.x) | **Plans:** 82 | **Timeline:** 2026-04-10 → 2026-04-22 (12 days post-initial-v1.0)

### What Was Built

- SSE-based async job pattern for GUI — `POST /async`, `GET /stream`, `GET /result`, `DELETE /{job_id}` with Cancel button (Phase 999.14)
- Stepper pipeline mode — per-stage execution (extract → transcribe → translate → write) with artifact persistence and auto-subfolder naming (Phases 999.27–999.28)
- Translation engine support: DeepL Free API, LibreTranslate, Argos Translate with batched context-aware translation (Phase 999.12)
- SSA subtitle output format via pysubs2 with configurable font/color styling in Settings (Phase 999.10, 999.13)
- CustomTkinter 6-tab redesign — each tab has its own log console, replaces 3-panel layout (Phases 999.29–999.30)
- GUI refactor series: `theme.py` (palette) → `styles.py` → `server.py` → `locale.py` separation (Phases 999.21–999.24)
- Configurable config file path via `GENSUBTITLES_CONFIG` env var (Phase 999.19)
- Retroactive VERIFICATION.md + Nyquist VALIDATION.md for all 10 core phases (Phases 11–13)
- Bilingual documentation update + standalone `docs/cli-tutorial.md` (Phases 999.18, 999.20)

### What Worked

- **Decimal phase numbering** (999.x) — continued to work perfectly for backlog features; no confusion with core phase numbering
- **Vertical slice phases** — even large features (SSE, stepper, tabbed GUI) were broken into 3–5 focused plans that executed cleanly
- **Refactor series** — doing the refactors as sequential phases (palette → styles → server → locale) meant each was small enough to complete without regressions
- **SSE pattern** — replacing blocking HTTP with SSE solved the timeout problem cleanly; Cancel support came for free via `threading.Event`
- **Per-tab log consoles** — moving logs into each tab eliminated the "silent progress bar" complaint and made the 6-tab redesign feel intentional

### What Was Inefficient

- **Three GUI layout redesigns** — the 3-panel layout (Phase 999.29) was planned and executed, then replaced by the 6-tab layout (Phase 999.30) almost immediately; the 3-panel work was mostly wasted effort
- **Retroactive verification was large** — Phases 11–13 took 7 plans to close documentation debt that should have been written per-phase during initial execution; each VALIDATION.md adds ~30 min if written at phase close vs 3 hours to retroactively write all of them
- **Duplicate MILESTONES.md entry** — the `milestone complete` CLI created an incomplete entry at the top of MILESTONES.md that required manual cleanup; accomplishments list was empty because `summary-extract` wasn't called

### Patterns Established

- `threading.Event` as `cancel_event` passed to `run_pipeline()` — clean cancellation contract between GUI and pipeline
- SSE format: `data: {"type": "progress", "step": N, "label": "..."}` — consistent event shape for GUI streaming
- Per-tab `_log_textbox` + `_log_to(textbox, msg)` helper — each tab owns its console; no global log routing needed
- `sanitize_stem()` + auto-subfolder in stepper work dir — prevents multiple videos overwriting each other's artifacts
- GUI refactor order: theme → styles → server → locale — each layer depends on the previous; doing them out of order would cause circular imports

### Key Lessons

1. **Don't build a layout you'll immediately replace** — the 3-panel redesign should have been skipped in favor of going straight to the 6-tab design; collect more context before a major layout rewrite
2. **Write VALIDATION.md at phase close, not retroactively** — 5 minutes per phase is far cheaper than Phases 11–13 (7 plans) to catch up
3. **`milestone complete` CLI needs summary-extract integration** — accomplishments list is always empty because the CLI doesn't call summary-extract; add a manual accomplishments step after CLI runs
4. **Backlog phases are real work** — the 999.x "backlog" grew to 27 phases and 52 plans; scope it as carefully as core phases

### Cost Observations

- All execution: claude-sonnet (execution), claude-opus (planning)
- Sessions: ~12 days of execution after initial v1.0
- Notable: Refactor phases (999.21–999.24) were extremely efficient — clear scope, no ambiguity, 1 plan each

---

## Cross-Milestone Trends

| Metric | v1.0 Core | v1.0 Full |
|--------|-----------|-----------|
| Phases | 16 | 40 |
| Plans | 30 | 82 |
| Timeline | 8 days | 20 days |
| Python LOC | ~1,602 | ~5,568 |
| Test LOC | — | ~3,096 |
| Git commits | ~147 | 434 |
