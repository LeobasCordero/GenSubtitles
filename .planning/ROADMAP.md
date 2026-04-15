# GenSubtitles -- Project Roadmap

## Milestones

- SHIPPED **v1.0 MVP** -- Phases 1 to 16 (shipped 2026-04-10) -- [archive](milestones/v1.0-ROADMAP.md)

---

## Phases

- [x] **Phase 1: Project Infrastructure** — Directory layout, dependencies, entry point scaffolding
 (completed 2026-04-02)
- [x] **Phase 2: Audio Extraction Module** — FFmpeg subprocess audio extraction to 16kHz mono WAV (completed 2026-04-02)
- [x] **Phase 3: Transcription Engine** — faster-whisper integration with VAD, device auto-detection (completed 2026-04-02)
- [x] **Phase 4: Translation Engine** — Argos Translate offline translation with on-demand model install (completed 2026-04-03)
- [x] **Phase 5: SRT Generation Module** — `srt` library segment-to-file conversion (1 plan) (completed 2026-04-03)
- [x] **Phase 6: Core Pipeline Assembly** — Wire all core modules into a single callable pipeline
 (completed 2026-04-06)
- [x] **Phase 7: CLI Interface** — Typer CLI with all flags, progress output, and exit codes (completed 2026-04-06)
- [x] **Phase 8: FastAPI REST API Core** — Upload endpoint, lifespan model loading, thread pool execution (completed 2026-04-07)
- [x] **Phase 9: FastAPI Extensions & Docs** — Languages endpoint, Uvicorn serve, OpenAPI docs (completed 2026-04-07)
- [x] **Phase 10: Documentation & End-to-End Validation** — README, examples, full pipeline test
 (completed 2026-04-10)
- [ ] **Phase 11: Retroactive Verification — Core Modules** — Formal VERIFICATION.md for phases 2–5 (Audio, Transcription, Translation, SRT)
- [ ] **Phase 12: Retroactive Verification + Pipeline Refactor** — Formal VERIFICATION.md for phases 6–7 + wire API router through run_pipeline()
- [ ] **Phase 13: Nyquist Compliance — All Phases** — Create/complete VALIDATION.md for all 10 phases

---

## Next Milestone

### Phase 1: Project Infrastructure

**Goal:** Establish the directory structure, pinned dependencies, and scaffolding so all subsequent phases build on a clean, reproducible foundation.  
**Requirements:** INF-01, INF-02, INF-04  
**Estimated complexity:** Low  
**Depends on:** Nothing (first phase)

**Plans:** 3/3 plans complete

Plans:
- [x] 01-01-PLAN.md — Project config files (pyproject.toml, requirements.txt, .gitignore, placeholder dirs)
- [x] 01-02-PLAN.md — Package skeleton (gensubtitles/ tree, core stubs, api stubs, cli stub, root main.py shim)
- [x] 01-03-PLAN.md — Environment + test scaffold + README (uv sync, tests/test_infrastructure.py, README.md)

### UAT Criteria

- [ ] Given a fresh clone, when `pip install -r requirements.txt` runs, then all packages install without dependency conflicts
- [ ] Given the workspace root, when listing directories, then `gensubtitles/core/`, `gensubtitles/api/`, `gensubtitles/cli/` all exist and each contains `__init__.py`
- [ ] Given `python main.py`, when the CLI entry point is invoked with no args, then a usage/help message is printed (not an ImportError or AttributeError)
- [ ] Given `requirements.txt`, then every package has a pinned version (`==` or `>=`) and no dependency is missing

---

### Phase 2: Audio Extraction Module

**Goal:** Implement FFmpeg-based audio extraction that takes any supported video format and outputs a 16kHz mono WAV file suitable for Whisper.  
**Requirements:** AUD-01, AUD-02, AUD-03, AUD-04  
**Estimated complexity:** Medium  
**Depends on:** Phase 1

**Plans:** 3 plans

Plans:
- [ ] 02-01-PLAN.md — Exceptions module (gensubtitles/exceptions.py) + test fixture infrastructure (tests/conftest.py)
- [ ] 02-02-PLAN.md — Implement gensubtitles/core/audio.py (extract_audio, audio_temp_context, SUPPORTED_EXTENSIONS)
- [ ] 02-03-PLAN.md — Write tests/test_audio.py (5 tests covering AUD-01–04)

### UAT Criteria

- [ ] Given a valid `.mp4` with an audio track, when `extract_audio(video, tmp.wav)` is called, then a WAV file is created at `tmp.wav` readable by `wave.open()` with `framerate==16000` and `nchannels==1`
- [ ] Given a `.mkv` file (different container), when `extract_audio` is called, then the same 16kHz mono WAV is produced without error
- [ ] Given a video file with no audio stream, when `extract_audio` is called, then a `RuntimeError` is raised whose message contains "audio"
- [ ] Given an unsupported extension (`.xyz`), when `extract_audio` is called, then a `ValueError` is raised before any FFmpeg subprocess is spawned
- [ ] Given FFmpeg is not installed, when `extract_audio` is called, then an `EnvironmentError` is raised with a message directing the user to install FFmpeg
- [ ] Given `audio_temp_context(video_path)` completes (normally or via exception), then the temp WAV file is removed from disk

---

### Phase 3: Transcription Engine

**Goal:** Implement a configurable faster-whisper transcription class that supports all model sizes, auto-detects device/language, applies VAD filtering, and materializes the segment generator before returning.  
**Requirements:** TRN-01, TRN-02, TRN-03, TRN-04, TRN-05, TRN-06  
**Estimated complexity:** High  
**Depends on:** Phase 1

**Plans:** 2/2 plans complete

Plans:
- [x] 03-01-PLAN.md — Implement gensubtitles/core/transcriber.py (WhisperTranscriber class + transcribe_audio)
- [x] 03-02-PLAN.md — Write tests/test_transcriber.py (25 unit tests, TRN-01 to TRN-06)

### Original Plan Items

1. **Implement `core/transcriber.py` module** — Create `gensubtitles/core/transcriber.py` with a `WhisperTranscriber` class
2. **Implement `__init__(model_size, device, compute_type)`** — Default `device="auto"`, `compute_type=None`; auto-select compute_type: `"float16"` for CUDA, `"int8"` for CPU; instantiate `WhisperModel(model_size, device=resolved_device, compute_type=resolved_compute_type)`
3. **Implement device auto-detection** — Check `torch.cuda.is_available()` (or catch ImportError); set `resolved_device = "cuda"` if available, `"cpu"` otherwise; log the resolved device
4. **Validate model_size values** — Reject unknown model sizes with a `ValueError` listing valid options: `tiny`, `base`, `small`, `medium`, `large-v1`, `large-v2`, `large-v3`, `turbo`, `distil-large-v3`
5. **Implement `transcribe(audio_path, language=None)` method** — Call `self.model.transcribe(audio_path, vad_filter=True, beam_size=5, language=language)`
6. **Materialize segments immediately** — On the very next line after `transcribe()`, call `segments = list(segments)` to force the generator and complete transcription before returning
7. **Return structured result** — Return `(segments: list, info.language: str)` as a named tuple `TranscriptionResult(segments=..., language=...)`
8. **Add `BatchedInferencePipeline` support (GPU)** — When `device=="cuda"`, wrap model in `BatchedInferencePipeline` with `batch_size=16` for 3–4x GPU throughput
9. **Expose a module-level convenience function** — `transcribe_audio(audio_path, model_size="small", device="auto", language=None) -> TranscriptionResult` that creates a transcriber and calls transcribe (for callers that don't need to reuse the model)

### UAT Criteria

- [ ] Given a WAV file of spoken English, when `transcribe()` is called, then `result.segments` is a non-empty list whose first item has `start`, `end` (floats), and `text` (non-empty string) attributes
- [ ] Given no `language` argument, when `transcribe()` returns, then `result.language` is a two-letter language code (e.g., `"en"`) and not `None`
- [ ] Given `model_size="tiny"` and `device="cpu"`, when `WhisperTranscriber` is initialized, then no exception is raised and `transcriber.model` is not `None`
- [ ] Given audio with 30 seconds of silence before speech, when `vad_filter=True` (always on), then no hallucinated subtitle segments appear for the silent portion
- [ ] Given CUDA unavailable and `device="auto"`, when `WhisperTranscriber` is initialized, then the model loads on CPU without error
- [ ] Given an invalid model size `"huge"`, when `WhisperTranscriber` is initialized, then a `ValueError` listing valid sizes is raised

---

### Phase 4: Translation Engine

**Goal:** Implement optional offline translation using Argos Translate that installs language models on first use, caches them locally, and skips translation when source equals target.  
**Requirements:** TRANS-01, TRANS-02, TRANS-03, TRANS-04, TRANS-05  
**Estimated complexity:** High  
**Depends on:** Phase 1

**Plans:** 2 plans

Plans:
- [x] 04-01-PLAN.md — Add tqdm dependency + implement gensubtitles/core/translator.py
- [x] 04-02-PLAN.md — Write tests/test_translator.py (18 tests, TRANS-01 to TRANS-05)

### UAT Criteria

- [ ] Given English segments and `target_lang="es"`, when `translate_segments()` is called, then each segment's `.text` is in Spanish and `.start`/`.end` are unchanged
- [ ] Given `source_lang == target_lang == "en"`, when `translate_segments()` is called, then the identical segment objects are returned without any translation call
- [ ] Given an uninstalled `en→fr` language pair, when `ensure_pair_installed("en", "fr")` is called, then the package is downloaded and subsequent `is_pair_available("en", "fr")` returns `True`
- [ ] Given an already-installed pair, when `ensure_pair_installed` is called a second time, then no HTTP request is made (model not re-downloaded)
- [ ] Given an unsupported pair (e.g., `"en"→"tlh"`), when `translate_segments()` is called, then a `ValueError` with the pair name in the message is raised

---

### Phase 5: SRT Generation Module

**Goal:** Convert a list of transcribed (optionally translated) segments to a valid SRT file using the `srt` library with correct timecode formatting and UTF-8 output.  
**Requirements:** SRT-01, SRT-02, SRT-03, SRT-04  
**Estimated complexity:** Low  
**Depends on:** Phase 1

**Plans:** 1 plan

Plans:
- [x] 05-01-PLAN.md — Implement srt_writer.py (segments_to_srt + write_srt) + 14-test TDD suite

### UAT Criteria

- [ ] Given segments with `start=0.0`, `end=3.5`, `text=" Hello world"`, when `segments_to_srt()` is called, then the output starts with `1\n00:00:00,000 --> 00:00:03,500\nHello world`
- [ ] Given a segment with leading/trailing whitespace in `.text`, when `segments_to_srt()` is called, then the SRT content has the text stripped
- [ ] Given a valid segment list, when `write_srt(segments, "output/test.srt")` is called, then the file exists, is readable as UTF-8, and parses via `srt.parse()` without error
- [ ] Given the SRT string produced by `segments_to_srt()`, when parsed with `list(srt.parse(output))`, then `len(parsed) == len(input_segments)` and `parsed[0].start == timedelta(seconds=segments[0].start)`
- [ ] Given an empty segments list, when `write_srt` is called, then no exception is raised and the output file is created (possibly empty)

---

### Phase 6: Core Pipeline Assembly

**Goal:** Wire audio extraction, transcription, translation, and SRT generation into a single callable pipeline function that manages temp files, emits progress, and returns a structured result.  
**Requirements:** AUD-01–04, TRN-01–06, TRANS-01–05, SRT-01–04 (integration)  
**Estimated complexity:** Medium  
**Depends on:** Phases 2, 3, 4, 5

**Plans:** 2/2 plans complete

Plans:
- [x] 06-01-PLAN.md — Extend TranscriptionResult with duration field + add PipelineError to exceptions.py + update transcriber tests
- [x] 06-02-PLAN.md — TDD: implement gensubtitles/core/pipeline.py (PipelineResult + run_pipeline) + test_pipeline.py

### UAT Criteria

- [ ] Given a real MP4 video with spoken audio, when `run_pipeline(video, "out.srt", model_size="tiny", target_lang=None, device="cpu")` is called, then `out.srt` is created and `result.segment_count > 0`
- [ ] Given any outcome (success or exception), when `run_pipeline` returns or raises, then no temp `.wav` files remain in `temp/` or the system temp directory
- [ ] Given `target_lang=None`, when `run_pipeline` runs, then the translation stage is skipped (no Argos model download is attempted)
- [ ] Given a non-existent `video_path`, when `run_pipeline` is called, then `FileNotFoundError` is raised before any FFmpeg subprocess is spawned
- [ ] Given a `progress_callback` function, when `run_pipeline` runs, then it is called exactly 4 times (once per stage) with increasing `current` values

---

### Phase 7: CLI Interface

**Goal:** Expose the pipeline as a polished command-line tool with all required flags, user-visible progress output, meaningful exit codes, and a `--help` that documents every option.  
**Requirements:** CLI-01, CLI-02, CLI-03, CLI-04  
**Estimated complexity:** Medium  
**Depends on:** Phase 6

**Plans:** 2/2 complete

Plans:
- [x] 07-01-PLAN.md — Implement gensubtitles/cli/main.py: 6 Typer flags + progress callback + error handling + exit codes
- [x] 07-02-PLAN.md — Write tests/test_cli.py: 8 CliRunner tests covering all CLI UAT criteria

### UAT Criteria

- [ ] Given `python main.py --input video.mp4 --output out.srt --model tiny`, when run on a valid video, then `out.srt` is created and the process exits with code `0`
- [ ] Given `python main.py --help`, when run, then all flags (`--input`, `--output`, `--model`, `--target-lang`, `--source-lang`, `--device`) are listed with descriptions
- [ ] Given `python main.py --input video.mp4` (no `--output`), when run, then the SRT is saved to a path derived from the input filename (e.g., `video.srt`)
- [ ] Given a missing `--input` flag, when run, then exit code is non-zero (1 or 2) and a usage error is printed to stderr
- [ ] Given a non-existent input file path, when run, then exit code is `1` and the error message names the missing file
- [ ] Given a valid video, when the pipeline runs, then progress lines `[1/4] Extracting audio...`, `[2/4] Transcribing...`, `[3/4] Translating...`, `[4/4] Writing SRT...` appear on stdout (translation line may be skipped if no `--target-lang`)

---

### Phase 8: FastAPI REST API Core

**Goal:** Implement the FastAPI application with model preloading via `lifespan`, a file-upload transcription endpoint that runs in the thread pool, and robust temp file lifecycle management.  
**Requirements:** API-01, API-02, API-03, API-04  
**Estimated complexity:** High  
**Depends on:** Phase 6

**Plans:** 3/3 plans complete

Plans:
- [x] 08-01-PLAN.md — FastAPI app with lifespan model loading + get_transcriber dependency (api/main.py, api/dependencies.py)
- [x] 08-02-PLAN.md — POST /subtitles endpoint: UploadFile copy → preloaded transcriber → FileResponse + BackgroundTask cleanup; wire router (api/routers/subtitles.py, api/main.py)
- [x] 08-03-PLAN.md — API test suite: 8 tests covering API-01 through API-04 with mocked deps (tests/test_api.py)

### UAT Criteria

- [ ] Given the API server is running, when `curl -X POST /subtitles -F "file=@video.mp4"` is sent, then the response body is a valid SRT string with status 200
- [ ] Given a large video file (50MB+), when uploaded via `POST /subtitles`, then the API does not crash and returns a valid SRT (UploadFile handles spooling)
- [ ] Given app startup, when `lifespan` runs, then `WhisperModel` is loaded exactly once (a debug log confirms model loading) and is accessible on subsequent requests without reload
- [ ] Given a sync `def` route handling a blocking transcription, when the route runs, then the async event loop remains unblocked for other requests (verified by sending two concurrent requests)
- [ ] Given an invalid (non-video) file upload, when `POST /subtitles` is called, then a 400 or 500 response with a `{"detail": ...}` JSON body is returned (not a 500 stack trace)
- [ ] Given `POST /subtitles` returns, then no temp video or SRT files remain on disk (BackgroundTask cleanup confirmed)

---

### Phase 9: FastAPI Extensions & API Documentation

**Goal:** Complete the REST API with the language-pairs endpoint, Uvicorn serve documentation, and confirm auto-generated OpenAPI docs are accessible.  
**Requirements:** API-05, API-06, API-07  
**Estimated complexity:** Medium  
**Depends on:** Phase 8

**Plans:** 2/2 plans complete

Plans:
- [x] 09-01-PLAN.md — GET /languages endpoint + CORS middleware + extended API tests (/docs, /openapi.json)
- [x] 09-02-PLAN.md — CLI serve subcommand (uvicorn.run) + 3 serve tests

### UAT Criteria

- [ ] Given the API is running, when `GET /languages` is called, then a JSON object with a `"pairs"` list is returned (empty list `[]` is acceptable if no models installed yet)
- [ ] Given the API is running, when navigating to `http://localhost:8000/docs`, then Swagger UI loads and shows `POST /subtitles` and `GET /languages` with their parameters
- [ ] Given `GET /openapi.json`, when called, then the response is valid JSON that includes `"paths"` with both endpoint definitions
- [ ] Given `uvicorn gensubtitles.api.main:app --port 8000`, when the server starts, then `GET /docs` returns HTTP 200
- [ ] Given `POST /subtitles?target_lang=es` with an English video, when called, then the returned SRT contains Spanish text

---

### Phase 10: Documentation & End-to-End Validation

**Goal:** Write complete user-facing documentation in README.md covering installation, CLI usage, API usage, and troubleshooting; validate the full pipeline with real video end-to-end.  
**Requirements:** INF-03  
**Estimated complexity:** Low  
**Depends on:** Phases 7, 9  
**Plans:** 3/3 plans complete

Plans:
- [x] 10-01-PLAN.md — Write README.md (English) with Installation, CLI/API usage, Language Translation, Troubleshooting
- [x] 10-02-PLAN.md — Write README.es.md (Spanish) as complete translation with code examples preserved
- [x] 10-03-PLAN.md — E2E validation with synthetic video: CLI + API paths, with/without translation

### UAT Criteria

- [x] Given a developer following only the README, when performing the installation steps on a clean machine (Linux, macOS, or Windows), then `python main.py --help` runs without import errors
- [x] Given the README CLI examples, when copy-pasted verbatim into a terminal with a valid sample video, then all example commands complete with exit code 0
- [x] Given a real MP4 file with English speech, when `python main.py --input sample.mp4 --model tiny` is run, then a `.srt` file is created with at least one subtitle entry and correct `HH:MM:SS,mmm --> HH:MM:SS,mmm` timecodes
- [x] Given the API running locally, when the curl example from the README is executed, then an HTTP 200 response with SRT content is received
- [x] Given the README troubleshooting section, then it addresses all three failure modes: missing FFmpeg, model download failure, and missing output directory

---

## Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Project Infrastructure | 3/3 | Complete | 2026-04-02 |
| 2. Audio Extraction Module | 3/3 | Complete | 2026-04-02 |
| 3. Transcription Engine | 2/2 | Complete | 2026-04-02 |
| 4. Translation Engine | 2/2 | Complete | 2026-04-03 |
| 5. SRT Generation Module | 1/1 | Complete | 2026-04-03 |
| 6. Core Pipeline Assembly | 2/2 | Complete | 2026-04-06 |
| 7. CLI Interface | 2/2 | Complete | 2026-04-06 |
| 8. FastAPI REST API Core | 3/3 | Complete | 2026-04-07 |
| 9. FastAPI Extensions & Docs | 2/2 | Complete | 2026-04-07 |
| 10. Documentation & End-to-End Validation | 3/3 | Complete | 2026-04-10 |
| 11. Retroactive Verification — Core Modules | 0/0 | Pending | — |
| 12. Retroactive Verification + Pipeline Refactor | 0/0 | Pending | — |
| 13. Nyquist Compliance — All Phases | 0/0 | Pending | — |

---

## Requirement Coverage

| Requirement | Phase | Status |
|-------------|-------|--------|
| INF-01 | Phase 1 | Complete |
| INF-02 | Phase 1 | Complete |
| INF-04 | Phase 1 | Complete |
| AUD-01 | Phase 2 | Complete (verification: Phase 11) |
| AUD-02 | Phase 2 | Complete (verification: Phase 11) |
| AUD-03 | Phase 2 | Complete (verification: Phase 11) |
| AUD-04 | Phase 2 | Complete (verification: Phase 11) |
| TRN-01 | Phase 3 | Complete (verification: Phase 11) |
| TRN-02 | Phase 3 | Complete (verification: Phase 11) |
| TRN-03 | Phase 3 | Complete (verification: Phase 11) |
| TRN-04 | Phase 3 | Complete (verification: Phase 11) |
| TRN-05 | Phase 3 | Complete (verification: Phase 11) |
| TRN-06 | Phase 3 | Complete (verification: Phase 11) |
| TRANS-01 | Phase 4 | Complete (verification: Phase 11) |
| TRANS-02 | Phase 4 | Complete (verification: Phase 11) |
| TRANS-03 | Phase 4 | Complete (verification: Phase 11) |
| TRANS-04 | Phase 4 | Complete (verification: Phase 11) |
| TRANS-05 | Phase 4 | Complete (verification: Phase 11) |
| SRT-01 | Phase 5 | Complete (verification: Phase 11) |
| SRT-02 | Phase 5 | Complete (verification: Phase 11) |
| SRT-03 | Phase 5 | Complete (verification: Phase 11) |
| SRT-04 | Phase 5 | Complete (verification: Phase 11) |
| CLI-01 | Phase 7 | Complete (verification: Phase 12) |
| CLI-02 | Phase 7 | Complete (verification: Phase 12) |
| CLI-03 | Phase 7 | Complete (verification: Phase 12) |
| CLI-04 | Phase 7 | Complete (verification: Phase 12) |
| API-01 | Phase 8 | Complete (integration: Phase 12) |
| API-02 | Phase 8 | Complete (integration: Phase 12) |
| API-03 | Phase 8 | Complete (integration: Phase 12) |
| API-04 | Phase 8 | Complete (integration: Phase 12) |
| API-05 | Phase 9 | Complete |
| API-06 | Phase 9 | Complete |
| API-07 | Phase 9 | Complete |
| INF-03 | Phase 10 | Complete |

**Coverage: 34/31 v1 requirements mapped** *(31 original + 3 split across Phase 8/9 from API-05/06/07) — all requirements covered ✓*

> **Note on pysrt → srt migration:** REQUIREMENTS.md references `srt` library (SRT-01 already corrected from pysrt). PROJECT.md still mentions `pysrt` in the pipeline description and Key Decisions table — recommend updating PROJECT.md to reflect `srt` (v3.5.3) as the chosen library per research finding.

---

### Phase 11: Retroactive Verification — Core Modules

**Goal:** Formally close the verification gate for phases 2–5 by running gsd-verify-work retroactively and producing a VERIFICATION.md for each phase. All code is complete and tests pass — this captures the formal exit record.
**Requirements:** AUD-01, AUD-02, AUD-03, AUD-04, TRN-01, TRN-02, TRN-03, TRN-04, TRN-05, TRN-06, TRANS-01, TRANS-02, TRANS-03, TRANS-04, TRANS-05, SRT-01, SRT-02, SRT-03, SRT-04
**Gap Closure:** Closes verification gaps from audit — phases 02, 03, 04, 05 missing VERIFICATION.md
**Estimated complexity:** Low
**Depends on:** Phase 10 (milestone audit complete)

**Plans:** 0 plans

### UAT Criteria

- [ ] Given Phase 02 directory, when verification runs, then VERIFICATION.md exists with status:passed and all AUD-01 to AUD-04 listed as verified
- [ ] Given Phase 03 directory, when verification runs, then VERIFICATION.md exists with status:passed and all TRN-01 to TRN-06 listed as verified
- [ ] Given Phase 04 directory, when verification runs, then VERIFICATION.md exists with status:passed and all TRANS-01 to TRANS-05 listed as verified
- [ ] Given Phase 05 directory, when verification runs, then VERIFICATION.md exists with status:passed and all SRT-01 to SRT-04 listed as verified

---

### Phase 12: Retroactive Verification + Pipeline Refactor

**Goal:** Formally verify phases 6–7 and close integration gap #1 from the audit: add an optional `transcriber=` parameter to `run_pipeline()` so the API router can reuse the preloaded model instead of reimplementing pipeline logic inline.
**Requirements:** CLI-01, CLI-02, CLI-03, CLI-04, API-01, API-02, API-03, API-04
**Gap Closure:** Closes verification gaps for phases 06 and 07; closes Integration Gap #1 (API router bypasses run_pipeline)
**Estimated complexity:** Medium
**Depends on:** Phase 11

**Plans:** 0 plans

### UAT Criteria

- [ ] Given Phase 06 directory, when verification runs, then VERIFICATION.md exists with status:passed
- [ ] Given Phase 07 directory, when verification runs, then VERIFICATION.md exists with status:passed and all CLI-01 to CLI-04 listed as verified
- [ ] Given `run_pipeline(..., transcriber=preloaded_instance)`, when called, then the preloaded transcriber is used and no new WhisperModel is instantiated
- [ ] Given `api/routers/subtitles.py`, when POST /subtitles is called, then `run_pipeline()` is invoked (not manual inline orchestration)
- [ ] Given both CLI and API paths, when run end-to-end, then both produce identical SRT output for the same input

---

### Phase 13: Nyquist Compliance — All Phases

**Goal:** Create or complete VALIDATION.md for all 10 v1.0 phases, achieving Nyquist wave 0 compliance across the milestone. Phase 05 is already compliant; all others need VALIDATION.md created or upgraded from draft.
**Requirements:** (Process compliance — no new feature requirements)
**Gap Closure:** Closes Nyquist tech debt for phases 01, 02 (draft→compliant) and phases 03, 04, 06, 07, 08, 09, 10 (missing→created)
**Estimated complexity:** Medium
**Depends on:** Phase 12

**Plans:** 0 plans

### UAT Criteria

- [ ] Given Phase 01 VALIDATION.md, when read, then `nyquist_compliant: true` and `wave_0_complete: true`
- [ ] Given Phase 02 VALIDATION.md, when read, then `nyquist_compliant: true` and `wave_0_complete: true`
- [ ] Given phases 03, 04, 06, 07, 08, 09, 10, when each is checked, then a VALIDATION.md exists with `nyquist_compliant: true`
- [ ] Given all 10 phases, when Nyquist status is tallied, then at least 9/10 phases report `nyquist_compliant: true`

---

## Backlog

### Phase 999.1: GUI Interface (BACKLOG)

**Goal:** Add a CustomTkinter desktop GUI so non-technical users can generate subtitles without using the CLI or REST API. The window exposes the 4 API-supported parameters (input file, output path, source language, target language), auto-launches the Uvicorn server on open, and shuts it down on close. Model size and device are fixed at server startup via lifespan configuration.
**Requirements:** GUI-01, GUI-02, GUI-03, GUI-04, GUI-05, GUI-06
**Plans:** 2/2 plans complete

Plans:
- [x] 999.1-01-PLAN.md — Package scaffold, customtkinter dependency, Uvicorn server thread, full UI layout
- [x] 999.1-02-PLAN.md — API integration (_on_generate), stage progress simulation, success+error feedback, CLI entry points

---

### Phase 999.2: GUI — Clear Fields Button (BACKLOG)

**Goal:** Add a "Clear" button to the GUI that resets all input fields (video path, subtitle path, model, language options) back to their default/empty state in a single click.
**Requirements:** TBD
**Plans:** 1/1 plans complete

Plans:
- [x] 999.2-01-PLAN.md — Add Clear button with reactive enable/disable + human verify

---

### Phase 999.3: GUI — Auto-populate Subtitle Path from Video (BACKLOG)

**Goal:** When a user selects a video file, automatically populate the subtitle output path field with the same directory and the same base filename as the video (e.g., selecting `/videos/movie.mp4` sets subtitle path to `/videos/movie.srt`).
**Requirements:** TBD
**Plans:** 1/1 plans complete

Plans:
- [x] 999.3-01-PLAN.md — Add auto-populate logic to `_browse_input` in `gui/main.py`

---

### Phase 999.4: GUI — Disable Fields During Pipeline (BACKLOG)

**Goal:** While the subtitle generation pipeline is running, all input fields and buttons (except a potential cancel/stop control) should be disabled/read-only to prevent mid-run modifications that could corrupt the operation.
**Requirements:** TBD
**Plans:** 1/1 plans complete

Plans:
- [x] 999.4-01-PLAN.md — Store 4 entry + 2 browse button widget refs; disable all 6 in _on_generate; re-enable in _finish_generate

---

### Phase 999.5: GUI — Elapsed Time Counter Above Progress Bar (BACKLOG)

**Goal:** Display an elapsed time counter (e.g., `00:01:23`) above the progress bar that starts from 00:00:00 when generation begins and counts up in real-time. The counter resets to zero at the start of every new subtitle generation run. After completion, display the final elapsed time.
**Requirements:** TBD
**Plans:** 1/1 plans complete

Plans:
- [x] 999.5-01-PLAN.md — Elapsed counter label, tick loop, lifecycle in _on_generate/_finish_generate (gensubtitles/gui/main.py)

---

### Phase 999.9: GUI — Form Polish (COMPLETED)

**Goal:** Three small form improvements bundled together: (1) add a visual `*` marker next to all mandatory fields (video input, output path) so users can identify required fields at a glance; (2) hide the source language input field — Whisper auto-detection is sufficient for most users and the field adds noise; (3) replace the target language free-text input with a dropdown offering "Spanish", "English", and "Other" to reduce user error. Merges former 999.6, 999.7, 999.8.
**Requirements:** TBD
**Plans:** 1/1 plans executed

Plans:
- [x] 999.9-01-PLAN.md — Mandatory field markers, source-lang hide, target-lang dropdown + Other entry (gensubtitles/gui/main.py)

---

### Phase 999.10: Feature Expansion — Language Support, Formats, Packaging, Settings & Help (BACKLOG)

**Goal:** Expand GenSubtitles with a set of user-facing features grouped into five areas: (1) extended translation language pairs (Japanese↔Spanish, English↔Spanish, Chinese↔Spanish, French↔Spanish, Norwegian↔Spanish, Korean↔Spanish); (2) additional format support (3GP video input, SSA subtitle output, SSA↔SRT conversion); (3) standalone portable packaging (single executable for Windows/macOS/Linux, no IDE or Python install required); (4) translation-only mode (accepts an existing SRT/SSA and translates it without transcription); (5) Settings menu (dark mode toggle, configurable defaults for source language and subtitle output path, app UI language); (6) Help menu with embedded tutorial, language pair listing, and About dialog; (7) Menu bar to host Settings and Help menus.
**Requirements:** TBD
**Plans:** 6/6 plans complete

Plans:
- [x] 999.10-01-PLAN.md — Core foundations: OutputFormat + SSA write/convert (srt_writer.py) + AppSettings persistence (settings.py); add pysubs2 + platformdirs deps
- [x] 999.10-02-PLAN.md — translate_file() in translator.py + CLI translate/convert subcommands + --format flag on generate
- [x] 999.10-03-PLAN.md — GUI dynamic language dropdowns from GET /languages (D-01/D-02) + output format SRT/SSA dropdown (D-08)
- [x] 999.10-04-PLAN.md — GUI Translate Subtitles tab (CTkTabview, translate/convert-only form, background thread handler) (D-05/D-09)
- [x] 999.10-05-PLAN.md — Menu bar (tkinter.Menu) + in-window Settings panel with persistence (D-12–D-17)
- [x] 999.10-06-PLAN.md — Help menu content: Tutorial dialog, Language Pairs dialog, About dialog + human verify (D-18)

**Captured features:**
- Soporte de pares de traducción: japonés→español, inglés→español, chino→español, francés→español, noruego→español, coreano→español
- Barra de menú con acceso a Settings y Ayuda
- Tutorial de uso integrado en la aplicación
- Modo de solo traducción de subtítulos (entrada: SRT/SSA existente, sin transcripción)
- Empaquetado portable standalone (ejecutable sin IDE ni Python — Windows, macOS, Linux)
- Soporte de formato de video 3GP como entrada
- Soporte de formato SSA en la salida de subtítulos
- Conversión bidireccional SSA ↔ SRT
- Menú Settings: dark mode, valores por defecto (idioma principal, ruta de salida relativa al video), idioma de la interfaz
- Menú Ayuda: tutorial, listado de idiomas disponibles, Acerca de...

---

---

### Phase 999.11: Subtitle Silence — VAD & Timestamp Quality (BACKLOG)

**Goal:** Reduce the duration a subtitle stays on screen during silence by tuning the VAD parameters exposed by faster-whisper, and enable word-level timestamps so each segment is cut exactly where speech ends instead of at the chunk boundary.
**Requirements:** TBD
**Plans:** 2/2 plans complete

Plans:
- [x] 999.11-01-PLAN.md — TDD: VAD params + word timestamps + wordless segment drop + default model=medium (transcriber.py + tests)
- [x] 999.11-02-PLAN.md — Docs: update README.md, README.es.md, and GUI tutorial for medium default

**Context captured:**
- Lower `min_silence_duration_ms` from default 2000ms to ~400ms so subtitles disappear faster after speech ends
- Add `speech_pad_ms` (200ms) and `min_speech_duration_ms` (250ms) to avoid residual noise segments
- Enable `word_timestamps=True` for precise per-word start/end times instead of chunk-level padding
- Consider bumping default model from `small` to `medium` for better English timestamp precision

---

### Phase 999.12: Translation Quality — Context-Aware & Engine Upgrade (BACKLOG)

**Goal:** Improve subtitle translation quality in two dimensions: (1) pass all segments as a single block to Argos Translate so it has sentence context, instead of translating each line independently; (2) add optional support for a higher-quality engine (DeepL Free API) as a configurable alternative to Argos.
**Requirements:** TBD
**Plans:** 4/4 plans complete

Plans:
- [x] 999.12-01-PLAN.md — Core translator: Argos batching + DeepL/LibreTranslate engine functions + AppSettings credentials
- [x] 999.12-02-PLAN.md — CLI --engine flag + pipeline.py forwarding + API engine query param
- [x] 999.12-03-PLAN.md — GUI engine CTkOptionMenu (show/hide with target lang + disable/enable cycle + wire to API)
- [x] 999.12-04-PLAN.md — Tests: batching correctness + engine dispatch + error cases

**Context captured:**
- Current: each segment `.text` is translated independently — no context between lines, leading to inconsistent pronouns, names, and idioms
- Improvement A: concatenate all segment texts with a delimiter, translate as one block, split back by delimiter — gives cross-sentence context to Argos
- Improvement B: optional DeepL Free API integration (500k chars/month free tier) as a quality-mode alternative; keep Argos as offline fallback
- Improvement C: optional LibreTranslate self-hosted integration for privacy-conscious users
- Pivot chain quality note: `ja→en` Argos model is the weakest link for Japanese→Spanish; better `ja→en` base quality would cascade to better `en→es` output

---

### Phase 999.13: Subtitle Style Settings (BACKLOG)

**Goal:** Add a subtitle styling submenu in Settings → Preferences where users can configure visual appearance of generated subtitles: font family, font size, text color, and outline/border color.
**Requirements:** STYLE-01, STYLE-02, STYLE-03, STYLE-04, STYLE-05, STYLE-06
**Plans:** 2/2 plans complete

Plans:
- [x] 999.13-01-PLAN.md — Backend: AppSettings style fields + write_ssa()/convert_srt_to_ssa() style parameter + TDD tests
- [x] 999.13-02-PLAN.md — GUI: Settings panel style section (font dropdown, size entry, color swatches), wire to AppSettings, apply to SSA output + human verify

**Context captured:**
- Applies primarily to SSA/ASS output format (which natively supports style metadata in the `[V4+ Styles]` section)
- SRT format has no standard styling — could write inline HTML tags (`<font color>`, `<b>`, `<i>`) supported by some players (VLC, YouTube) but ignored by others
- Fields to expose: font family (text input or dropdown of common fonts), font size (integer spinner), primary color (color picker), outline color (color picker), outline width (numeric)
- Should persist through `AppSettings` (new `subtitle_style` nested config or flat fields)
- Default values should match current hardcoded SSA defaults in `srt_writer.py`

---

### Phase 999.16: GUI — UI Language Setting Not Working (BACKLOG)

**Goal:** The UI Language option in Settings changes the stored preference but does not relabel the interface — all labels remain in the original language after selecting a different one. Fix the runtime language-switch mechanism so that selecting a UI language immediately (or after a prompted restart) updates all visible labels, menu entries, buttons, and dialog text throughout the app.
**Requirements:** TBD
**Plans:** 1/1 plans executed

Plans:
- [x] 999.16-01-PLAN.md — String registry + stored widget refs + _apply_ui_language(); wired into __init__ + _save_settings; dialogs use _s(); human verify

**Context captured:**
- Setting is persisted via `AppSettings` but the GUI widgets are not re-rendered or re-translated after the change
- Options: (A) full re-render on language change (rebuild all CTk widgets); (B) prompt user to restart the app and apply on next launch; (C) use a centralized string registry (`i18n` dict) and bind labels to reactive string vars so they update automatically
- Affected scope: all `CTkLabel`, `CTkButton`, menu entries, dialog titles, and error messages

---

### Phase 999.17: GUI — Installed Language Pairs Showing Duplicates (BACKLOG)

**Goal:** The "Installed Language Pairs" dialog in the Help menu shows duplicate entries for the same language pair. Deduplicate the list before rendering so each `from→to` pair appears exactly once.
**Requirements:** DEDUP-01
**Plans:** 1 plan

Plans:
- [x] 999.17-01-PLAN.md — Deduplicate list_installed_pairs() + regression test

**Context captured:**
- Root likely in `list_installed_pairs()` in `translator.py` — Argos Translate may register the same package multiple times after reinstall or index refresh
- Fix: deduplicate with `{(p["from"], p["to"]) for p in pairs}` before passing to the UI
- Also apply deduplication in `GET /languages` API response for consistency

---

### Phase 999.18: Docs — README Update (BACKLOG)

**Goal:** Update README.md (and README.es.md) to reflect all features added after v1.0: GUI interface, translation engines (DeepL, LibreTranslate), SSA output format, translate-only mode, settings persistence, subtitle style options, and the Help/Settings menus. Also document known limitations (DeepL/LibreTranslate not yet active in GUI).
**Requirements:** TBD
**Plans:** 2/2 plans complete

Plans:
- [x] 999.18-01-PLAN.md — Rewrite README.md with new audience-split structure
- [x] 999.18-02-PLAN.md — Update README.es.md to mirror README.md structure

**Context captured:**
- Current README covers CLI + basic API only — GUI section is minimal
- Sections to add/update: GUI usage walkthrough, translation engine comparison table, SSA output format, configuration file location and schema, troubleshooting for new error types (timeout, marker mismatch fallback)
- Both English and Spanish README must be kept in sync

---

### Phase 999.19: Config — Configurable JSON Config File Location (BACKLOG)

**Goal:** Allow users to specify a custom path for the configuration JSON file instead of the hardcoded default (platformdirs AppData location). Useful for portable installs, shared network configs, or version-controlled project-level settings. Should be configurable via CLI flag (`--config`), environment variable (`GENSUBTITLES_CONFIG`), or both.
**Requirements:** TBD
**Plans:** 2/2 plans complete

Plans:
- [x] 999.19-01-PLAN.md — settings_path() GENSUBTITLES_CONFIG env var override + regression tests
- [x] 999.19-02-PLAN.md — GUI Settings panel: config path label + Open Folder button

**Context captured:**
- Current config path is resolved by `platformdirs.user_config_dir()` in `settings.py` — make this overridable
- Priority order: CLI flag > env var > default platformdirs path
- GUI should display the active config path in Settings so users know where changes are stored
- Portable mode: if a `gensubtitles.json` exists next to `main.py`, auto-use it (zero-config for portable packaging)

---

### Phase 999.20: Docs — CLI Tutorial (BACKLOG)

**Goal:** Add a dedicated CLI tutorial — either as a new section in README.md or as a standalone `docs/cli-tutorial.md` — that walks through the full CLI workflow step by step: installation, basic transcription, transcription + translation, format options (SRT/SSA), the `serve` subcommand, and the `translate` subcommand for existing subtitle files. Targeted at technical users who don't need the GUI.
**Requirements:** TBD
**Plans:** 0 plans

Plans:
- [ ] TBD (promote with /gsd-review-backlog when ready)

**Context captured:**
- Current README has short CLI examples but no end-to-end tutorial narrative
- Should cover: `python main.py generate`, `python main.py translate`, `python main.py serve`, `--engine` flag, `--format` flag, `--model` sizes and their trade-offs
- Include expected output snippets and timings for each model size
- Cross-link from Help menu "Tutorial" dialog (which currently shows GUI-oriented steps)

---

### Phase 999.15: GUI — UI Bug Fixes & Polish

**Goal:** Fix a batch of small but visible UI bugs in the GUI: (1) "Open folder" button persists after clicking "Generate subtitles" a second time — must be hidden at the start of each new generation run; (2) DeepL and LibreTranslate engine options are visible in the dropdown even though they are disabled — should be hidden or clearly marked as unavailable; (3) target language set in the config file is not reflected in the UI on startup — the dropdown must initialize from `AppSettings`; (4) the "About GenSubtitles" dialog in the Help menu does not follow the app's UI rules for spacing, fonts, and colors; (5) in light theme, disabled buttons are nearly invisible — update their disabled color to a more visible, accessible value.
**Requirements:** TBD
**Plans:** 1/1 plans complete

Plans:
- [x] 999.15-01-PLAN.md — AppSettings target_lang + engine filtering + open folder hide + About dialog colors + disabled button text

**Context captured:**
- BUG-1: `_open_folder` button shown after first generation is not hidden when "Generate subtitles" is clicked again — hide it at the top of `_on_generate`
- BUG-2: DeepL and LibreTranslate are shown in engine CTkOptionMenu but are non-functional; either remove from the list or add "(unavailable)" label and disable selection
- BUG-3: `AppSettings.target_lang` is loaded from config but not used to pre-select the target language dropdown in `__init__` of the GUI
- BUG-4: About dialog text uses default tkinter fonts/colors, not the app's CustomTkinter theme — apply consistent `CTkLabel` styling, padding, and font
- BUG-5: Light theme disabled button foreground color blends into the background — set an explicit `fg_color` / `text_color_disabled` that passes WCAG AA contrast in light mode

---

### Phase 999.14: GUI — HTTP Timeout During Subtitle Generation

**Goal:** Replace the blocking `POST /subtitles` HTTP call with an SSE-based async job pattern so long transcription+translation runs never hit a read timeout. Add a Cancel button that lets the user abort a running job.
**Requirements:** TBD
**Plans:** 3/3 plans complete

Plans:
- [ ] 999.14-01-PLAN.md — API: SSE job endpoints (POST /async, GET /stream, GET /result, DELETE /{job_id})
- [ ] 999.14-02-PLAN.md — GUI: Replace blocking call with SSE flow + Cancel button
- [ ] 999.14-03-PLAN.md — Tests: SSE endpoints + pipeline cancellation

**Context captured:**
- Error: `HTTPConnectionPool(host='127.0.0.1', port=8000): Read timed out. (read timeout=3600)`
- Timeout is already set to 3600 s (1 hour) but long transcription+translation jobs can exceed it
- Options: (A) remove read timeout entirely for local calls; (B) stream progress via SSE so the connection stays alive; (C) run the pipeline asynchronously and poll a `/status` endpoint; (D) show a user-friendly retry dialog instead of the raw exception

---

---

### Phase 999.21: REFACTOR — Palette Colors Separation (COMPLETE)

**Goal:** Separate palette color definitions into their own module/file so additional color palettes can be added in the future without touching component code.
**Requirements:** TBD
**Plans:** 1/1 plans executed

Plans:
- [x] 999.21-01-PLAN.md — Create theme.py and migrate all color/typography definitions from main.py

---

### Phase 999.22: REFACTOR — Separate GUI Styles from Components (BACKLOG)

**Goal:** Extract all styling definitions (fonts, sizes, paddings, widget configurations) out of GUI component classes into a dedicated styles layer, keeping components focused on layout and behaviour.
**Requirements:** TBD
**Plans:** 2/2 plans complete

Plans:
- [x] 999.22-01-PLAN.md — Create gensubtitles/gui/styles.py (spacing/dimension constants + widget-style helpers)
- [x] 999.22-02-PLAN.md — Update main.py: apply-after-construction pattern + replace magic numbers + simplify _apply_theme()

---

### Phase 999.23: REFACTOR — Apply SOLID Principles to GUI (BACKLOG)

**Goal:** Apply SRP to `gensubtitles/gui/main.py` by extracting the server lifecycle concern into a new dedicated module `gensubtitles/gui/server.py` (widget-free, callback-based), continuing the theme → styles → locale refactor series.
**Requirements:** TBD
**Plans:** 1/1 plans complete

Plans:
- [x] 999.23-01-PLAN.md — Create server.py (extract start/stop/polling loop + constants) + migrate main.py (5 BASE_URL refs, _start_server wrapper, on_closing)

---

### Phase 999.24: REFACTOR — Localisation Separation (BACKLOG)

**Goal:** Move all user-facing strings and locale/i18n logic into a dedicated localisation layer, decoupling translation concerns from GUI components and making it easy to add or swap languages.
**Requirements:** TBD
**Plans:** 1/1 plans complete

Plans:
- [x] 999.24-01-PLAN.md — Create locale.py (move _STRINGS + s()/set_language()/s_lang()) + migrate 66 call sites in main.py

---

### Phase 999.25: BUG — GUI `s()` TypeError int not callable in `_finish_generate` (COMPLETE)

**Goal:** Fix `TypeError: 'int' object is not callable` raised in `_finish_generate` when calling `s("msg_generation_failed_title")` — `s` is shadowed by an integer somewhere before the call.
**Requirements:** TBD
**Plans:** 0 plans (resolved without a dedicated plan — fixed as side effect of 999.24)

Error context:
```
File "gensubtitles\gui\main.py", line 1143, in _finish_generate
    messagebox.showerror(s("msg_generation_failed_title"), error)
TypeError: 'int' object is not callable
```

**Resolution:** Fixed during Phase 999.24 (localisation refactor). `_finish_generate` originally used `s = elapsed % 60` which shadowed the `s()` locale function. The variable was renamed to `secs` in the current codebase — verified 2026-04-15.

---

### Phase 999.26: Console Log Display for User Tracking (BACKLOG)

**Goal:** Display a real-time console/log panel so users can track exactly what the pipeline is doing at each step — model loading, audio extraction, transcription progress, translation, and SRT writing — instead of watching a silent progress bar.
**Requirements:** TBD
**Plans:** 0 plans

Plans:
- [ ] TBD (promote with /gsd-review-backlog when ready)

**Context captured:**
- Users have no visibility into what's happening during long runs (e.g. large model download, slow transcription)
- Each pipeline stage should emit a timestamped log line (e.g. `[00:03] Transcribing audio...`, `[00:47] Translating 128 segments...`)
- GUI: scrollable read-only text area or log panel below the progress bar that streams messages in real time
- CLI: `--verbose` flag (or always-on) that prints stage banners to stdout
- API: could surface as SSE events (ties into Phase 999.14 async/SSE work)
- Backend: a logging callback/hook injected into `pipeline.py` stages so the core doesn't depend on any UI layer

---

### Phase 999.27: Stepper Mode for Pipeline Steps (BACKLOG)

**Goal:** Add a step-by-step execution mode so users can run one pipeline stage at a time (extract audio → transcribe → translate → write SRT), with the option to run the full pipeline in one shot (existing behaviour) as the default. Each step saves its output so subsequent steps can resume without repeating work already done.
**Requirements:** TBD
**Plans:** 0 plans

Plans:
- [ ] TBD (promote with /gsd-review-backlog when ready)

**Context captured:**
- Motivation: a failure in the last step (e.g. translation crash) currently discards all prior work; step mode lets the user retry from the failing stage
- Default first-screen option: "Generate subtitles (all steps)" — preserves current one-click UX
- Step-by-step mode exposes individual buttons: "1. Extract Audio", "2. Transcribe", "3. Translate", "4. Write SRT"
- Each step should output an intermediate artefact (WAV, JSON/segments, translated segments, SRT) that the next step reads as input
- GUI: a stepper widget (horizontal step indicator) showing completed/current/pending stages; each stage activates its action button only when its prerequisite output exists
- CLI: `--step extract|transcribe|translate|write` flag to run a single stage; `--input-from` flag to point at a prior stage's output
- Ties into Phase 999.26 (console log) — each step completion is a natural log event

---

*Roadmap created: 2026-04-02*  
*Last updated: 2026-04-15 — Phase 999.25 marked COMPLETE (bug already fixed in 999.24 refactor); backlog items 999.26 and 999.27 added*
