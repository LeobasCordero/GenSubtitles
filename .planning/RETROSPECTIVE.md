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

## Cross-Milestone Trends

| Metric | v1.0 |
|--------|------|
| Phases | 16 |
| Plans | 30 |
| Timeline | 8 days |
| Tests | 73 |
| Python LOC | ~1,602 |
| Test runtime | 2.87s |
