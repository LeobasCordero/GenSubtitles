# GenSubtitles — Project State

*GSD project memory. Updated after each phase completes or key decision is made.*

## Current Status

- **Milestone:** v1
- **Active Phase:** None — project initialized, ready to start Phase 1
- **Last action:** Project initialized with GSD v1.30.0 (2026-04-02)

## Milestone Progress

| Phase | Title | Status |
|-------|-------|--------|
| 1 | Project Infrastructure | ⏳ Not started |
| 2 | Audio Extraction Module | ⏳ Not started |
| 3 | Transcription Engine | ⏳ Not started |
| 4 | Translation Engine | ⏳ Not started |
| 5 | SRT Generation Module | ⏳ Not started |
| 6 | Core Pipeline Assembly | ⏳ Not started |
| 7 | CLI Interface | ⏳ Not started |
| 8 | FastAPI REST API Core | ⏳ Not started |
| 9 | FastAPI Extensions & Docs | ⏳ Not started |
| 10 | Documentation & End-to-End Validation | ⏳ Not started |

## Key Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-04-02 | Use `srt` library instead of `pysrt` | pysrt unmaintained since 2020; `srt` v3.5.3 actively maintained, no deps, 30% faster |
| 2026-04-02 | Use `subprocess` for FFmpeg (not ffmpeg-python) | ffmpeg-python abandoned (2019, 480 open issues) |
| 2026-04-02 | Audio extraction at `-ar 16000 -ac 1` | Whisper's native sample rate; reduces file size and processing time |
| 2026-04-02 | Always `list(segments)` from faster-whisper | segments is a lazy generator — materializing avoids subtle bugs |
| 2026-04-02 | FastAPI sync `def` for transcription routes | CPU-bound work; sync routes get auto thread pool, avoids event loop blocking |
| 2026-04-02 | Load models once in FastAPI `lifespan` | Avoids re-loading large models per request (~1-5GB) |

## Blockers & Notes

*(None)*

---
*GSD v1.30.0 — initialized 2026-04-02*
