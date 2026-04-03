# GenSubtitles

## What This Is

GenSubtitles is a Python CLI/API tool that automatically generates subtitles from video files. Given a video, it extracts the audio, transcribes it using faster-whisper, optionally translates the transcription via Argos Translate, and outputs a properly formatted SRT file.

## Core Value

Accurate, offline-capable subtitle generation from any video — no external API keys required.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

(None yet — ship to validate)

### Active

- [ ] Accept a video file as input and extract its audio track via FFmpeg
- [ ] Transcribe audio to text using faster-whisper (local, offline)
- [ ] Detect source language automatically
- [ ] Translate transcription to target language using Argos Translate (offline)
- [ ] Generate a valid SRT subtitle file using the `srt` library
- [ ] Expose functionality via FastAPI REST API (Uvicorn server)
- [ ] CLI interface for direct usage without API
- [ ] Support multiple input video formats (mp4, mkv, avi, mov, etc.)
- [ ] Support multiple target languages for translation

### Out of Scope

- Cloud-based speech recognition (e.g., OpenAI Whisper API) — keeping fully offline/local
- Video editing or burning subtitles into video — output is SRT only
- Real-time streaming transcription — file-based only for v1
- Web UI — CLI + REST API is sufficient for v1

## Context

- **Pipeline:** Video → Audio (FFmpeg) → Transcription (faster-whisper) → Translation (Argos Translate) → SRT (`srt` v3.5.3)
- **Python 3.11+** is the baseline — no older version compatibility required
- The project is a skeleton at initialization: `main.py` entry point exists, `requirements.txt` is empty
- No existing tests, no CI/CD configured yet
- Argos Translate downloads language models on first use — this needs to be handled gracefully

## Constraints

- **Tech Stack**: Python 3.11+, FFmpeg (system dep), faster-whisper, Argos Translate, `srt` (replaces pysrt), FastAPI, Uvicorn
- **Offline**: Core transcription and translation must work without internet after initial model download
- **Performance**: Whisper model selection should balance speed vs accuracy (allow configurable model size)
- **OS**: Should run on Linux/macOS/Windows with FFmpeg installed

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| faster-whisper over openai-whisper | 4x faster, lower memory, CTranslate2 backend | — Pending |
| Argos Translate for translation | Fully offline, no API keys, supports 100+ language pairs | — Pending |
| FastAPI for API layer | Modern, async, auto-generated docs, lightweight | — Pending |
| `srt` library for SRT generation | pysrt unmaintained (2020); `srt` v3.5.3 is actively maintained, no deps, 30% faster | — Pending |

---
*Last updated: 2026-04-02 — Phase 1 (Project Infrastructure) complete — package skeleton, pinned deps, test scaffold, README in place*
