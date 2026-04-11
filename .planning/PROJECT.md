# GenSubtitles

## What This Is

GenSubtitles is a fully offline Python CLI/API/GUI tool that generates SRT subtitle files from any video. It extracts audio via FFmpeg, transcribes with faster-whisper, optionally translates via Argos Translate, and outputs a properly formatted SRT file. A CustomTkinter desktop GUI provides a point-and-click interface on top of the same pipeline.

## Core Value

Accurate, offline-capable subtitle generation from any video — no external API keys required.

## Requirements

### Validated

<!-- Shipped and confirmed valuable in v1.0. -->

- ✓ Accept video file input and extract audio via FFmpeg (16kHz mono WAV) — v1.0
- ✓ Support mp4, mkv, avi, mov, webm input formats — v1.0
- ✓ Transcribe audio to text using faster-whisper (local, offline) — v1.0
- ✓ Auto-detect source language — v1.0
- ✓ Translate transcription using Argos Translate (offline, on-demand model install) — v1.0
- ✓ Generate valid SRT file using `srt` library — v1.0
- ✓ FastAPI REST API: `POST /subtitles`, `GET /languages`, Uvicorn, OpenAPI docs — v1.0
- ✓ Typer CLI with `--input`, `--output`, `--model`, `--target-lang` flags — v1.0
- ✓ Desktop GUI (CustomTkinter) with full generate workflow, elapsed timer, Clear button — v1.0
- ✓ 73-test suite covering all core modules — v1.0

### Active

<!-- Requirements for v2.0 — none defined yet. Run /gsd-new-milestone to begin. -->

### Out of Scope

- Cloud-based speech recognition (e.g., OpenAI Whisper API) — keeping fully offline/local
- Video editing or burning subtitles into video — output is SRT only
- Real-time streaming transcription — file-based only
- Subtitle burn-in — out of scope (v2.0 ADV-01 candidate)

## Context

- **Pipeline:** Video → Audio (FFmpeg, 16kHz mono) → Transcription (faster-whisper) → Translation (Argos Translate, optional) → SRT (`srt` v3.5.3)
- **GUI:** CustomTkinter desktop app (`gensubtitles gui`) wraps the same pipeline via FastAPI
- **Python 3.11+** | ~1,602 LOC in `gensubtitles/` package | 73 tests
- **v1.0 shipped:** 2026-04-02 → 2026-04-10 (8 days, ~147 commits)
- Argos Translate downloads language models on first use and caches locally

## Constraints

- **Tech Stack**: Python 3.11+, FFmpeg (system dep), faster-whisper, Argos Translate, `srt` (replaces pysrt), FastAPI, Uvicorn
- **Offline**: Core transcription and translation must work without internet after initial model download
- **Performance**: Whisper model selection should balance speed vs accuracy (allow configurable model size)
- **OS**: Should run on Linux/macOS/Windows with FFmpeg installed

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| faster-whisper over openai-whisper | 4x faster, lower memory, CTranslate2 backend | ✓ Good — delivers fast local transcription |
| Argos Translate for translation | Fully offline, no API keys, supports 100+ language pairs | ✓ Good — works well, on-demand download UX acceptable |
| FastAPI for API layer | Modern, async, auto-generated docs, lightweight | ✓ Good — OpenAPI docs at /docs, thread-pool for CPU-bound work |
| `srt` library for SRT generation | pysrt unmaintained (2020); `srt` v3.5.3 is actively maintained, no deps, 30% faster | ✓ Good — no issues in v1.0 |
| CustomTkinter for GUI | Cross-platform, modern look, wraps tkinter | ✓ Good — desktop GUI ships without extra dependencies |

---
*Last updated: 2026-04-10 after v1.0 milestone — full pipeline, CLI, API, GUI, and 73-test suite shipped*
