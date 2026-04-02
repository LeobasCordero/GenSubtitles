# GenSubtitles — Project Roadmap

**Milestone:** v1.0  
**Granularity:** Fine (10 phases)  
**Coverage:** 31/31 v1 requirements mapped ✓  
**Generated:** 2026-04-02

---

## Phases

- [ ] **Phase 1: Project Infrastructure** — Directory layout, dependencies, entry point scaffolding
- [ ] **Phase 2: Audio Extraction Module** — FFmpeg subprocess audio extraction to 16kHz mono WAV
- [ ] **Phase 3: Transcription Engine** — faster-whisper integration with VAD, device auto-detection
- [ ] **Phase 4: Translation Engine** — Argos Translate offline translation with on-demand model install
- [ ] **Phase 5: SRT Generation Module** — `srt` library segment-to-file conversion
- [ ] **Phase 6: Core Pipeline Assembly** — Wire all core modules into a single callable pipeline
- [ ] **Phase 7: CLI Interface** — Typer CLI with all flags, progress output, and exit codes
- [ ] **Phase 8: FastAPI REST API Core** — Upload endpoint, lifespan model loading, thread pool execution
- [ ] **Phase 9: FastAPI Extensions & Docs** — Languages endpoint, Uvicorn serve, OpenAPI docs
- [ ] **Phase 10: Documentation & End-to-End Validation** — README, examples, full pipeline test

---

## Phase Details

### Phase 1: Project Infrastructure

**Goal:** Establish the directory structure, pinned dependencies, and scaffolding so all subsequent phases build on a clean, reproducible foundation.  
**Requirements:** INF-01, INF-02, INF-04  
**Estimated complexity:** Low  
**Depends on:** Nothing (first phase)

**Plans:** 3 plans

Plans:
- [x] 01-01-PLAN.md — Project config files (pyproject.toml, requirements.txt, .gitignore, placeholder dirs)
- [ ] 01-02-PLAN.md — Package skeleton (gensubtitles/ tree, core stubs, api stubs, cli stub, root main.py shim)
- [ ] 01-03-PLAN.md — Environment + test scaffold + README (uv sync, tests/test_infrastructure.py, README.md)

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

### Plans

1. **Implement `core/audio.py` module** — Create `gensubtitles/core/audio.py` with an `extract_audio(video_path: str, output_path: str) -> None` function
2. **Build FFmpeg subprocess command** — Construct `["ffmpeg", "-i", video_path, "-vn", "-ar", "16000", "-ac", "1", "-f", "wav", "-y", output_path]`; use `subprocess.run(..., capture_output=True, text=True)`
3. **Validate return code and raise on error** — If `result.returncode != 0`, raise `RuntimeError(f"FFmpeg failed: {result.stderr}")` with the full stderr for diagnostics
4. **Validate input file extension** — Check extension against `{".mp4", ".mkv", ".avi", ".mov", ".webm"}`; raise `ValueError` with the rejected extension before invoking FFmpeg
5. **Handle missing audio track** — Parse FFmpeg stderr for "no audio" indicators; raise `RuntimeError("No audio track found in video")` with a descriptive message distinct from generic FFmpeg errors
6. **Implement temp-file cleanup helper** — Add `audio_temp_context(video_path: str)` context manager using `tempfile.NamedTemporaryFile(suffix=".wav", delete=False)` that yields the temp path and deletes it on exit
7. **Check FFmpeg availability** — At module import, or lazily on first call, check that `ffmpeg` is on PATH via `shutil.which("ffmpeg")`; raise `EnvironmentError("FFmpeg not found on PATH")` if absent
8. **Write unit smoke test** — Using a tiny synthetic video (1-second mp4 generated via FFmpeg in the test itself), verify `extract_audio` produces a WAV file with the correct properties

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

### Plans

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

### Plans

1. **Implement `core/translator.py` module** — Create `gensubtitles/core/translator.py` with functions for translation, package management, and pair listing
2. **Implement `list_installed_pairs() -> list[dict]`** — Return list of `{"from": code, "to": code}` dicts from `argostranslate.translate.get_installed_languages()`
3. **Implement `ensure_pair_installed(from_code, to_code) -> None`** — Check installed packages; if pair missing, call `update_package_index()` then download and `install_from_path()`; skip download if already installed
4. **Implement package index update** — Wrap `argostranslate.package.update_package_index()` with a try/except; log a warning if index update fails (offline mode); do not crash if already-installed packages are sufficient
5. **Implement `is_pair_available(from_code, to_code) -> bool`** — Check both installed packages and available (remote) packages; raise `ValueError(f"Language pair '{from_code}→{to_code}' is not available. Call list_installed_pairs() to see options.")` if the pair is neither installed nor available
6. **Implement `translate_segments(segments, source_lang, target_lang) -> list`** — If `source_lang == target_lang`, return segments unchanged; otherwise call `ensure_pair_installed`, then translate each segment's text via `argostranslate.translate.translate(text, source_lang, target_lang)`
7. **Return translated segments preserving timestamps** — Build a new list from each original segment, replacing only `.text`; use a simple dataclass `TranslatedSegment(start, end, text)` for consistent typing
8. **Model cache verification** — Verify cached models are not re-downloaded on repeated calls by inspecting installed packages list before each `ensure_pair_installed` call
9. **Handle pivot translation gracefully** — Document in docstring that Argos automatically pivots through English if the direct pair is missing; surface this in the pair-availability error message

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

### Plans

1. **Implement `core/srt_writer.py` module** — Create `gensubtitles/core/srt_writer.py` with two public functions: `segments_to_srt` and `write_srt`
2. **Implement `segments_to_srt(segments) -> str`** — Iterate segments (1-indexed), convert `seg.start`/`seg.end` floats to `datetime.timedelta(seconds=float)`, strip `seg.text`, build `srt.Subtitle(index, start, end, content)`, collect into list
3. **Compose SRT string** — Call `srt.compose(subtitles)` to produce the final SRT-formatted string; never manually format timecodes
4. **Implement `write_srt(segments, output_path: str) -> None`** — Call `segments_to_srt()`, ensure parent directory of `output_path` exists (`Path(output_path).parent.mkdir(parents=True, exist_ok=True)`), write to file as UTF-8
5. **Handle empty segment list** — If `segments` is empty, write an empty file (0 bytes) and log a warning rather than raising an exception
6. **Validate round-trip integrity** — In tests, parse output with `srt.parse()` and verify entry count matches input segment count and timestamps match within 1ms tolerance
7. **Preserve original text when not translated** — Confirm `SRT-04`: if no translation occurred, `seg.text.strip()` is the exact content written to the SRT entry

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

### Plans

1. **Implement `core/pipeline.py`** — Create `gensubtitles/core/pipeline.py` with `run_pipeline(video_path, output_path, model_size, target_lang, source_lang, device, progress_callback) -> PipelineResult`
2. **Define `PipelineResult` dataclass** — Fields: `srt_path: str`, `detected_language: str`, `segment_count: int`, `audio_duration_seconds: float`
3. **Manage temp audio file lifecycle** — Use `audio_temp_context(video_path)` (Phase 2) as a context manager; guarantee cleanup via `try/finally` even on exception
4. **Implement stage-by-stage pipeline** — Stage 1: extract_audio → Stage 2: transcribe → Stage 3: translate (conditional) → Stage 4: write_srt; emit progress callback with stage name and stage index before each stage
5. **Implement `progress_callback` protocol** — Signature `(stage: str, current: int, total: int) -> None`; default to a no-op lambda if not provided; pass `("Extracting audio", 1, 4)`, `("Transcribing", 2, 4)`, etc.
6. **Validate inputs at entry** — Check `video_path` exists (`Path.is_file()`), `output_path` parent is writable; raise `FileNotFoundError` and `PermissionError` respectively with clear messages
7. **Wrap stage errors with context** — Catch exceptions from each stage, re-raise as `PipelineError(stage="audio_extraction", cause=original_exc)` (custom exception subclassing `RuntimeError`) so callers know which stage failed
8. **Add `source_lang=None` / `target_lang=None` passthrough** — When `target_lang is None`, skip translation stage entirely; pass `source_lang` directly to `transcribe()` (or `None` for auto-detect)

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

### Plans

1. **Implement `cli/main.py` with Typer** — Create `gensubtitles/cli/main.py`; instantiate a `typer.Typer()` app with a single `generate` command (also set as default callback so `python main.py` works)
2. **Wire `--input` flag** — `input: Path = typer.Option(..., "--input", "-i", help="Path to input video file", exists=True, readable=True)`
3. **Wire `--output` flag** — `output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output SRT path (defaults to input filename with .srt extension)")`; auto-derive default from input stem if not provided
4. **Wire `--model` flag** — `model: str = typer.Option("small", "--model", "-m", help="Whisper model size: tiny/base/small/medium/large-v1/large-v2/large-v3/turbo")`
5. **Wire `--target-lang` and `--source-lang` flags** — `target_lang: Optional[str] = typer.Option(None, "--target-lang", "-t", help="Target language code for translation (e.g. 'es'). Omit to keep source language.")` ; `source_lang: Optional[str] = typer.Option(None, "--source-lang", "-s", help="Source language code. Omit for auto-detection.")`
6. **Wire `--device` flag** — `device: str = typer.Option("auto", "--device", help="Compute device: auto/cpu/cuda")`
7. **Implement stage progress printing** — Pass a `progress_callback` to `run_pipeline` that prints `[{current}/{total}] {stage}...` to stdout using `typer.echo()`
8. **Implement error handling and exit codes** — Catch all exceptions in the CLI handler; print to stderr via `typer.echo(str(e), err=True)`; call `raise typer.Exit(code=1)` on error, `raise typer.Exit(code=0)` on success
9. **Update `main.py` entry shim** — `from gensubtitles.cli.main import app; app()` so `python main.py [args]` works identically to the installed script

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

### Plans

1. **Implement `api/main.py`** — Create `gensubtitles/api/main.py`; define `FastAPI(title="GenSubtitles", lifespan=lifespan)` app
2. **Implement `lifespan` context manager** — Use `@asynccontextmanager async def lifespan(app)` pattern; load `WhisperModel` and set `app.state.whisper_model`; log startup/shutdown; yield; cleanup on shutdown
3. **Implement `api/dependencies.py`** — Create `get_whisper_model(request: Request) -> WhisperModel` dependency that reads from `request.app.state.whisper_model`; injectable via `Depends(get_whisper_model)`
4. **Implement `api/routers/subtitles.py`** — Create router with `POST /subtitles` as a **sync `def` route** (not `async def`) so FastAPI automatically routes it to the thread pool executor
5. **Implement UploadFile → NamedTemporaryFile copy** — Inside the route, open a `NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix)` and `shutil.copyfileobj(file.file, tmp)` to get a real disk path for FFmpeg
6. **Run pipeline in sync route** — Call `run_pipeline(tmp_video_path, tmp_srt_path, model_size=..., ...)` directly; `def` route + FastAPI = auto threadpool, no manual `run_in_executor` needed
7. **Return SRT as FileResponse** — Use `FileResponse(tmp_srt_path, media_type="text/plain; charset=utf-8", filename="subtitles.srt")` and schedule temp file cleanup via `BackgroundTasks`
8. **Implement error handlers** — `@app.exception_handler(FileNotFoundError)` → 400; `@app.exception_handler(RuntimeError)` → 500 with `{"detail": str(e)}`; include `HTTPException` for malformed requests
9. **Accept model and language query params** — `model_size: str = Query(default="small")`, `target_lang: Optional[str] = Query(default=None)`, `source_lang: Optional[str] = Query(default=None)` on the POST route
10. **Verify `python-multipart` in requirements.txt** — Confirm it is listed (FastAPI will 400 on every upload without it)

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

### Plans

1. **Implement `GET /languages` endpoint** — Add to `api/routers/subtitles.py`; return `{"pairs": [{"from": code, "to": code}, ...]}` using `list_installed_pairs()` from `core/translator.py`
2. **Include router in app** — Register the subtitles router in `api/main.py` with `app.include_router(subtitles_router, prefix="")` or a `/api/v1` prefix
3. **Add query parameter passthrough to `POST /subtitles`** — Confirm `model_size`, `target_lang`, `source_lang` query params from Phase 8 are wired through to `run_pipeline`
4. **Document Uvicorn startup** — In README and in API module docstring: `uvicorn gensubtitles.api.main:app --host 0.0.0.0 --port 8000 --reload`
5. **Add `--serve` flag to CLI** — Add `serve` sub-command or `--serve` flag to `cli/main.py` that programmatically calls `uvicorn.run("gensubtitles.api.main:app", host=..., port=...)`
6. **Verify `/docs` Swagger UI** — Navigate to `http://localhost:8000/docs`; ensure both `POST /subtitles` and `GET /languages` appear with correct parameter schemas
7. **Verify `/openapi.json`** — Confirm the JSON schema is valid and includes all endpoints, parameters, and response schemas
8. **Add CORS middleware (configurable)** — Add `CORSMiddleware` to `api/main.py` with `allow_origins=["*"]` as a dev default; document how to restrict in production

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

### Plans

1. **Write Installation section** — Cover prerequisites (Python 3.11+, FFmpeg) with platform-specific install commands; pip install from requirements.txt; initial model download note
2. **Write CLI Usage section** — Document all flags with defaults and show 3–5 example commands (basic run, with translation, custom model, custom output path)
3. **Write API Usage section** — Document startup (`uvicorn ...`); show `curl` examples for `POST /subtitles` and `GET /languages`; mention `/docs` for interactive exploration
4. **Document model size tradeoffs** — Add table: model name / approximate size / relative speed / relative accuracy / recommended use case
5. **Document language model download behavior** — Explain that Argos models are downloaded on first use (internet required); models are cached at OS-appropriate path; subsequent runs are offline
6. **Document CUDA/GPU setup** — Note CUDA 12 + cuDNN 9 requirement for GPU mode; how to override `--device cpu` if CUDA setup is incorrect
7. **Add Troubleshooting section** — Cover: FFmpeg not on PATH, CUDA errors, Argos model download failures, permissions on output directory
8. **Run end-to-end CLI test** — Using a real MP4 with speech: `python main.py --input sample.mp4 --output test.srt --model tiny`; verify SRT file is created with correct timecodes
9. **Run end-to-end API test** — Start uvicorn; send `curl -F "file=@sample.mp4" http://localhost:8000/subtitles`; verify SRT is returned in response body

### UAT Criteria

- [ ] Given a developer following only the README, when performing the installation steps on a clean machine (Linux, macOS, or Windows), then `python main.py --help` runs without import errors
- [ ] Given the README CLI examples, when copy-pasted verbatim into a terminal with a valid sample video, then all example commands complete with exit code 0
- [ ] Given a real MP4 file with English speech, when `python main.py --input sample.mp4 --model tiny` is run, then a `.srt` file is created with at least one subtitle entry and correct `HH:MM:SS,mmm --> HH:MM:SS,mmm` timecodes
- [ ] Given the API running locally, when the curl example from the README is executed, then an HTTP 200 response with SRT content is received
- [ ] Given the README troubleshooting section, then it addresses all three failure modes: missing FFmpeg, model download failure, and missing output directory

---

## Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Project Infrastructure | 0/7 | Not started | — |
| 2. Audio Extraction Module | 0/8 | Not started | — |
| 3. Transcription Engine | 0/9 | Not started | — |
| 4. Translation Engine | 0/9 | Not started | — |
| 5. SRT Generation Module | 0/7 | Not started | — |
| 6. Core Pipeline Assembly | 0/8 | Not started | — |
| 7. CLI Interface | 0/9 | Not started | — |
| 8. FastAPI REST API Core | 0/10 | Not started | — |
| 9. FastAPI Extensions & Docs | 0/8 | Not started | — |
| 10. Documentation & End-to-End Validation | 0/9 | Not started | — |

---

## Requirement Coverage

| Requirement | Phase | Status |
|-------------|-------|--------|
| INF-01 | Phase 1 | Pending |
| INF-02 | Phase 1 | Pending |
| INF-04 | Phase 1 | Pending |
| AUD-01 | Phase 2 | Pending |
| AUD-02 | Phase 2 | Pending |
| AUD-03 | Phase 2 | Pending |
| AUD-04 | Phase 2 | Pending |
| TRN-01 | Phase 3 | Pending |
| TRN-02 | Phase 3 | Pending |
| TRN-03 | Phase 3 | Pending |
| TRN-04 | Phase 3 | Pending |
| TRN-05 | Phase 3 | Pending |
| TRN-06 | Phase 3 | Pending |
| TRANS-01 | Phase 4 | Pending |
| TRANS-02 | Phase 4 | Pending |
| TRANS-03 | Phase 4 | Pending |
| TRANS-04 | Phase 4 | Pending |
| TRANS-05 | Phase 4 | Pending |
| SRT-01 | Phase 5 | Pending |
| SRT-02 | Phase 5 | Pending |
| SRT-03 | Phase 5 | Pending |
| SRT-04 | Phase 5 | Pending |
| CLI-01 | Phase 7 | Pending |
| CLI-02 | Phase 7 | Pending |
| CLI-03 | Phase 7 | Pending |
| CLI-04 | Phase 7 | Pending |
| API-01 | Phase 8 | Pending |
| API-02 | Phase 8 | Pending |
| API-03 | Phase 8 | Pending |
| API-04 | Phase 8 | Pending |
| API-05 | Phase 9 | Pending |
| API-06 | Phase 9 | Pending |
| API-07 | Phase 9 | Pending |
| INF-03 | Phase 10 | Pending |

**Coverage: 34/31 v1 requirements mapped** *(31 original + 3 split across Phase 8/9 from API-05/06/07) — all requirements covered ✓*

> **Note on pysrt → srt migration:** REQUIREMENTS.md references `srt` library (SRT-01 already corrected from pysrt). PROJECT.md still mentions `pysrt` in the pipeline description and Key Decisions table — recommend updating PROJECT.md to reflect `srt` (v3.5.3) as the chosen library per research finding.

---

*Roadmap created: 2026-04-02*  
*Last updated: 2026-04-02 — Initial roadmap from requirements + research*
