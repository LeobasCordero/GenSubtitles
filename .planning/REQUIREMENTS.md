# Requirements: GenSubtitles

**Defined:** 2026-04-02
**Core Value:** Accurate, offline-capable subtitle generation from any video — no external API keys required.

## v1 Requirements

### Audio Extraction

- [ ] **AUD-01**: System accepts a video file path as input (mp4, mkv, avi, mov, webm)
- [ ] **AUD-02**: Audio is extracted from video using FFmpeg subprocess at 16kHz mono (WAV/PCM)
- [ ] **AUD-03**: Extraction handles missing audio track gracefully with clear error message
- [ ] **AUD-04**: Temporary audio files are cleaned up after processing

### Transcription

- [ ] **TRN-01**: Audio is transcribed using faster-whisper (local, offline)
- [ ] **TRN-02**: Source language is detected automatically (no manual input required)
- [ ] **TRN-03**: Configurable Whisper model size (tiny/base/small/medium/large) via CLI flag or API param
- [ ] **TRN-04**: VAD filter is applied to suppress hallucinations on silence
- [ ] **TRN-05**: Whisper segments generator is fully consumed before downstream processing
- [ ] **TRN-06**: CPU and GPU (CUDA) execution are both supported; device auto-detected

### Translation

- [ ] **TRANS-01**: Transcription can be translated to a target language using Argos Translate (offline)
- [ ] **TRANS-02**: Translation is optional — skipped when source and target language are the same
- [ ] **TRANS-03**: Language model packages are installed programmatically on first use
- [ ] **TRANS-04**: System lists available language pairs and fails gracefully if a pair is unsupported
- [ ] **TRANS-05**: Models are downloaded once and cached locally (not re-downloaded on each run)

### SRT Generation

- [ ] **SRT-01**: Output is a valid SRT file using the `srt` library (replaces unmaintained pysrt)
- [ ] **SRT-02**: Whisper float timestamps (seconds) are correctly converted to SRT timecodes (HH:MM:SS,mmm)
- [ ] **SRT-03**: SRT file is saved to a configurable output path
- [ ] **SRT-04**: SRT entries preserve original segment text (translated if translation is enabled)

### CLI Interface

- [ ] **CLI-01**: `python main.py` accepts `--input`, `--output`, `--model`, `--target-lang` flags
- [ ] **CLI-02**: `--help` shows all available options with descriptions
- [ ] **CLI-03**: Progress is printed to stdout (extraction → transcription → translation → SRT)
- [ ] **CLI-04**: Exit code 0 on success, non-zero on error

### REST API (FastAPI)

- [ ] **API-01**: POST `/subtitles` endpoint accepts video file upload and returns SRT file
- [ ] **API-02**: Upload handler copies UploadFile to named temp file before passing to FFmpeg
- [ ] **API-03**: Transcription runs in thread pool executor (not blocking async event loop)
- [ ] **API-04**: Models are loaded once at application startup via FastAPI `lifespan` context
- [ ] **API-05**: GET `/languages` endpoint returns list of supported translation language pairs
- [ ] **API-06**: API is served via Uvicorn; startup command documented in README
- [ ] **API-07**: Auto-generated OpenAPI docs available at `/docs`

### Project Infrastructure

- [x] **INF-01**: `requirements.txt` lists all dependencies with pinned versions
- [x] **INF-02**: Project structure follows `core/` + `api/` + `cli/` separation
- [ ] **INF-03**: README documents installation, CLI usage, and API usage with examples
- [x] **INF-04**: FFmpeg as system dependency is documented with install instructions

## v2 Requirements

### Advanced Features

- **ADV-01**: Subtitle burn-in — embed SRT into video output (FFmpeg overlay)
- **ADV-02**: Batch processing — accept a directory of videos
- **ADV-03**: WebVTT output format in addition to SRT
- **ADV-04**: Speaker diarization (who said what)
- **ADV-05**: Word-level timestamps in SRT (karaoke style)

### Deployment

- **DEP-01**: Docker image with FFmpeg and all Python deps pre-installed
- **DEP-02**: GitHub Actions CI — lint + test on push

## Out of Scope

| Feature | Reason |
|---------|--------|
| Cloud speech recognition (OpenAI Whisper API) | Breaks offline requirement |
| Web UI | CLI + REST API is sufficient for v1 |
| Real-time streaming transcription | File-based only for v1; streaming adds significant complexity |
| Database / job queue | Synchronous processing only for v1 |
| Authentication on API | Internal tool; auth deferred to v2 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUD-01 to AUD-04 | Phase 1 | Pending |
| TRN-01 to TRN-06 | Phase 2 | Pending |
| TRANS-01 to TRANS-05 | Phase 3 | Pending |
| SRT-01 to SRT-04 | Phase 4 | Pending |
| CLI-01 to CLI-04 | Phase 5 | Pending |
| API-01 to API-07 | Phase 6 | Pending |
| INF-01 to INF-04 | Phase 7 | Pending |

**Coverage:**
- v1 requirements: 31 total
- Mapped to phases: 31
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-02*
*Last updated: 2026-04-02 — Project initialized*
