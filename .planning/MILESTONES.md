# Milestones

## v1.0 GenSubtitles MVP (Shipped: 2026-04-22)

**Phases completed:** 40 phases, 82 plans  
**Timeline:** 2026-04-02 → 2026-04-22 (20 days)  
**Python LOC:** ~5,568 (gensubtitles package) | ~3,096 (tests) | **Git commits:** 434

**Key accomplishments:**

- Full offline subtitle pipeline: Video → FFmpeg (16kHz WAV) → faster-whisper → Argos Translate → SRT
- FastAPI REST API with SSE-based async job pattern, Cancel button, `POST /subtitles`, `GET /languages`, OpenAPI docs
- Typer CLI with all flags, progress output, exit codes, and stepper mode (`--step` flag for per-stage execution)
- CustomTkinter desktop GUI — 6-tab redesign (Generate, Translate Subtitles, Extract, Transcribe, Translate, Write SRT) with per-tab log consoles
- SSE-based async job pattern replacing blocking HTTP call — long transcription runs no longer timeout
- Stepper pipeline mode — run each stage independently with artifact persistence between stages
- Translation engine support: Argos (offline), DeepL, LibreTranslate; SSA output format; translate-only mode
- GUI refactor series: palette → styles → server module → locale separation (Phases 999.21–999.24)
- Retroactive verification + Nyquist compliance across all 10 core phases (Phases 11–13)
- Bilingual documentation (EN + ES) with standalone CLI tutorial at `docs/cli-tutorial.md`

**Archive:** `.planning/milestones/v1.0-ROADMAP.md` | `.planning/milestones/v1.0-REQUIREMENTS.md`

---
