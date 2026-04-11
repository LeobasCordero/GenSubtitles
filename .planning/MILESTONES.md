# Milestones

## v1.0 GenSubtitles MVP (Shipped: 2026-04-11)

**Phases completed:** 16 phases, 30 plans  
**Timeline:** 2026-04-02 → 2026-04-10 (8 days)  
**Python LOC:** ~1,602 (gensubtitles package) | **Git commits:** ~147

**Key accomplishments:**

- Full offline subtitle pipeline: Video → FFmpeg (16kHz WAV) → faster-whisper → Argos Translate → SRT
- FastAPI REST API with file-upload endpoint (`POST /subtitles`), language list (`GET /languages`), and OpenAPI docs
- Typer CLI with `--input`, `--output`, `--model`, `--target-lang` flags, progress printing, and exit codes
- CustomTkinter desktop GUI with generate workflow, stage progress, elapsed timer, reactive Clear button, and field disable during pipeline
- 73-test suite with full mock coverage across all core modules (audio, transcription, translation, SRT, pipeline, CLI, API)
- English + Spanish README with install, CLI usage, and API usage documentation

**Tech debt carried forward:**
- Human E2E verification for `POST /subtitles` requires real Argos Translate + faster-whisper models (noted in v1.0-MILESTONE-AUDIT.md)

**Archive:** `.planning/milestones/v1.0-ROADMAP.md` | `.planning/milestones/v1.0-REQUIREMENTS.md`

---
