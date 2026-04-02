# Research Summary: GenSubtitles

**Domain:** Python CLI + REST API tool for automatic video subtitle generation  
**Pipeline:** Video → Audio (FFmpeg) → Transcription (faster-whisper) → Translation (Argos Translate) → SRT output  
**Researched:** 2026-04-02  
**Overall confidence:** HIGH (all sources verified against official docs/PyPI/GitHub)

---

## 1. faster-whisper Integration

**Latest version:** 1.2.1 (Oct 31, 2025) — actively maintained (21.9k stars)  
**Source:** https://github.com/SYSTRAN/faster-whisper, https://pypi.org/project/faster-whisper/

### Model Sizes
Available: `tiny`, `base`, `small`, `medium`, `large-v1`, `large-v2`, `large-v3`, `turbo`, `distil-large-v3`  
- **CPU / low-memory:** `small` (int8) or `medium` (int8) — good accuracy/speed tradeoff  
- **GPU with headroom:** `large-v3` (fp16) or `turbo` (fp16) — best accuracy  
- Models auto-download from HuggingFace Hub on first use (to `~/.cache/huggingface/hub`)  
- Custom model path: `WhisperModel("/path/to/local/dir")`

### Device Selection
```python
# GPU (CUDA 12 + cuDNN 9 required)
model = WhisperModel("large-v3", device="cuda", compute_type="float16")
# GPU with less VRAM
model = WhisperModel("large-v3", device="cuda", compute_type="int8_float16")
# CPU (recommended for portability)
model = WhisperModel("medium", device="cpu", compute_type="int8")
```
**GPU requirement gotcha:** Requires **CUDA 12** + **cuDNN 9** specifically. For CUDA 11 pin `ctranslate2==3.24.0`; for CUDA 12 + cuDNN 8 pin `ctranslate2==4.4.0`.

### Batching
Use `BatchedInferencePipeline` for GPU throughput (3-4x faster than unbatched):
```python
from faster_whisper import WhisperModel, BatchedInferencePipeline
model = WhisperModel("turbo", device="cuda", compute_type="float16")
batched_model = BatchedInferencePipeline(model=model)
segments, info = batched_model.transcribe("audio.wav", batch_size=16)
```
VAD filter is enabled by default in batched mode.

### Segment Handling (CRITICAL)
**`segments` is a generator — transcription only starts when you iterate.**
```python
segments, info = model.transcribe("audio.wav", beam_size=5)
segments = list(segments)  # Forces transcription to complete here
```
Each segment object has:
- `segment.start` — float, seconds
- `segment.end` — float, seconds  
- `segment.text` — transcribed text (includes leading space)

### Other Useful Options
- `vad_filter=True` — removes silence via Silero VAD (reduces hallucinations)
- `word_timestamps=True` — word-level granularity under `segment.words`
- `language="en"` — skip language detection for known-language content
- `condition_on_previous_text=False` — recommended for distil models

### Key Insight: FFmpeg Not Required for Transcription
faster-whisper bundles PyAV for audio decoding internally — it does **not** need system FFmpeg to read audio files. FFmpeg is only needed in this pipeline for the video→audio extraction step.

---

## 2. Argos Translate Integration

**Latest version:** 1.11.0 (Feb 2, 2026) — maintained  
**Source:** https://github.com/argosopentech/argos-translate, https://pypi.org/project/argostranslate/

### Programmatic Package Installation
```python
import argostranslate.package
import argostranslate.translate

# Step 1: Fetch package index (requires internet on first run)
argostranslate.package.update_package_index()

# Step 2: Find the language pair you need
available_packages = argostranslate.package.get_available_packages()
package = next(
    filter(lambda x: x.from_code == "en" and x.to_code == "es", available_packages)
)

# Step 3: Download and install
argostranslate.package.install_from_path(package.download())

# Step 4: Translate
translated = argostranslate.translate.translate("Hello world", "en", "es")
```

### Offline Usage
- Language models are `.argosmodel` files (zip archives with CTranslate2 weights)
- Pre-download and install via `install_from_path("/path/to/file.argosmodel")`
- Installed models stored at `~/.local/share/argos-translate` (Linux/Mac) or `%APPDATA%/argos-translate` (Windows)
- Cache at `~/.local/cache/argos-translate`
- **For production:** pre-install all needed language pairs during app setup/Docker build; don't rely on runtime internet access

### Language Pair Availability
37+ languages supported: Arabic, Azerbaijani, Chinese, Czech, Danish, Dutch, English, Finnish, French, German, Greek, Hebrew, Hindi, Hungarian, Indonesian, Italian, Japanese, Korean, Malay, Persian, Polish, Portuguese, Russian, Slovak, Spanish, Swedish, Turkish, Ukrainian, Urdu, and more.  
Browse: https://www.argosopentech.com/argospm/index/

### Pivot Translation (Automatic)
If you have `es→en` and `en→fr` installed but not `es→fr`, Argos automatically pivots through English. Quality is lower but avoids needing every pair installed.

### GPU Acceleration
Set environment variable before import: `ARGOS_DEVICE_TYPE=cuda` (or `auto`). Passed through to CTranslate2.

### Translation Quality Note
Argos Translate is offline/free but quality is mediocre compared to DeepL or Google Translate. For subtitle use-cases where nuance matters less than speed, it is acceptable for common language pairs (en↔es, en↔fr, en↔de). Less common pairs will have noticeably lower quality.

---

## 3. FFmpeg: Python Integration Approach

### Recommendation: Direct `subprocess` for Audio Extraction
**Do not use `ffmpeg-python`** (PyPI: `ffmpeg-python` v0.2.0 — last released July 2019, 480+ open issues, no recent commits). It is effectively abandoned.

**Direct subprocess is the correct approach** for the simple audio-extraction task this project needs:

```python
import subprocess
import tempfile
import os

def extract_audio(video_path: str, output_path: str) -> None:
    """Extract audio from video as 16kHz mono WAV (optimal for Whisper)."""
    cmd = [
        "ffmpeg", "-i", video_path,
        "-vn",           # no video
        "-ar", "16000",  # 16kHz sample rate (Whisper's native)
        "-ac", "1",      # mono
        "-f", "wav",
        "-y",            # overwrite output
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg error: {result.stderr}")
```

System FFmpeg must be installed and on PATH. This is a reasonable deployment requirement.

### Why Not `moviepy`?
MoviePy is heavy (depends on NumPy, decorator, imageio, etc.), has its own FFmpeg bundling complexity, and is overkill for a single audio extraction command.

### Temp File Pattern for API
For the API endpoint, save uploaded video to `tempfile.NamedTemporaryFile`, extract audio to another temp file, process, then clean up both:
```python
with tempfile.TemporaryDirectory() as tmpdir:
    video_path = os.path.join(tmpdir, "input.mp4")
    audio_path = os.path.join(tmpdir, "audio.wav")
    # write uploaded content to video_path
    extract_audio(video_path, audio_path)
    # transcribe from audio_path
```

---

## 4. FastAPI: File Upload Best Practices

**Latest version:** 0.135.3 — actively maintained  
**Source:** https://fastapi.tiangolo.com/tutorial/request-files/

### UploadFile (Use This, Not `bytes`)
`UploadFile` uses a `SpooledTemporaryFile` — stored in memory up to a size threshold, then spills to disk automatically. This means large video files won't cause OOM.

```python
from fastapi import FastAPI, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse
import shutil, tempfile, os

@app.post("/transcribe")
async def transcribe_video(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    source_lang: str = "auto",
    target_lang: str | None = None,
):
    # Save to disk before processing (SpooledTemporaryFile may not have a real path)
    with tempfile.NamedTemporaryFile(delete=False, suffix=file.filename) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
    
    background_tasks.add_task(process_and_cleanup, tmp_path, ...)
    return {"message": "Processing started", "job_id": "..."}
```

### Required Dependency
```
pip install python-multipart
```
FastAPI will raise a 400 error without it when receiving file uploads.

### Background Tasks vs. Blocking
Transcription is CPU/GPU-bound and can take 30s–several minutes. Options:
1. **`BackgroundTasks`** (simple, same process): Returns 202 immediately, processes in background. Client must poll for result. Works fine for single-user / low-concurrency scenarios.
2. **`asyncio.run_in_executor`** (better for CPU-bound): Runs blocking transcription in a thread pool, won't block the event loop.
3. **Celery + Redis/RabbitMQ** (production scale): FastAPI docs explicitly recommend this for heavy background computation requiring separate processes.

For an MVP/CLI-first approach, BackgroundTasks + a simple in-memory job status dict is sufficient.

### File Size Limits
Uvicorn has no default upload size limit. Set one via middleware or Starlette's `LimitUploadSize` if needed. For production, put a reverse proxy (nginx) in front with a body size limit.

### Sync vs Async Endpoint
Use `def` (not `async def`) for endpoints that do blocking I/O so FastAPI runs them in the threadpool automatically:
```python
@app.post("/transcribe/sync")
def transcribe_video_sync(file: UploadFile):  # def = runs in threadpool
    ...
```

---

## 5. SRT Generation: `srt` Library (Recommended over `pysrt`)

### Recommendation: Use `srt` (not `pysrt`)
- **`pysrt`** (v1.1.2, Jan 2020): Last release was 6 years ago, 22 open issues. Effectively unmaintained.
- **`srt`** (v3.5.3, Mar 2023): MIT license, no dependencies, ~30% faster than pysrt, 100% test coverage, actively used in production. **Use this instead.**

### Mapping Whisper Segments to SRT Entries
```python
import srt
import datetime

def segments_to_srt(segments) -> str:
    """Convert faster-whisper segments to SRT string."""
    subs = []
    for i, seg in enumerate(segments, start=1):
        start = datetime.timedelta(seconds=seg.start)
        end = datetime.timedelta(seconds=seg.end)
        content = seg.text.strip()
        subs.append(srt.Subtitle(index=i, start=start, end=end, content=content))
    return srt.compose(subs)
```

Key details:
- `seg.start` and `seg.end` are floats in seconds → wrap with `datetime.timedelta(seconds=...)`
- `seg.text` has a leading space — always `.strip()` it
- `srt.compose()` handles all SRT formatting (index numbering, timecode formatting `HH:MM:SS,mmm`)

### SRT Timecode Format
SRT uses `HH:MM:SS,mmm` (note comma, not period). The `srt` library handles this correctly. Do **not** manually format timecodes.

### Writing to File
```python
srt_content = segments_to_srt(segments)
with open("output.srt", "w", encoding="utf-8") as f:
    f.write(srt_content)
```
Always write SRT files as UTF-8.

---

## 6. Project Structure: Python CLI + API Hybrid

### Recommended Layout
```
gensubtitles/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── transcriber.py     # faster-whisper logic
│   ├── translator.py      # argos-translate logic  
│   ├── audio.py           # ffmpeg audio extraction
│   └── srt_writer.py      # srt assembly
├── api/
│   ├── __init__.py
│   ├── main.py            # FastAPI app + lifespan
│   ├── routers/
│   │   └── subtitles.py   # POST /transcribe etc.
│   └── dependencies.py    # model loading, config
├── cli/
│   └── main.py            # Click/Typer CLI entrypoint
main.py                    # top-level entrypoint (delegates to cli or api)
requirements.txt
pyproject.toml
models/                    # downloaded Whisper models (gitignored)
temp/                      # temp files during processing (gitignored)
output/                    # generated SRT files (gitignored)
```

### Key Conventions
- **`core/`** contains the pure pipeline logic — no FastAPI, no CLI. Both surfaces import from here.
- **CLI** uses Typer or Click (Typer is more modern, integrates with Python type hints).
- **Model loading** happens once at API startup via FastAPI `lifespan` context manager (not on every request).
- **Shared model instance** stored in `api/dependencies.py` as a module-level singleton, injected via `Depends()`.

### Model Loading Pattern (API)
```python
# api/main.py
from contextlib import asynccontextmanager
from faster_whisper import WhisperModel

whisper_model: WhisperModel | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global whisper_model
    whisper_model = WhisperModel("medium", device="cpu", compute_type="int8")
    yield
    whisper_model = None

app = FastAPI(lifespan=lifespan)
```

---

## 7. Common Pitfalls & Known Issues

### faster-whisper
1. **Generator not materialized:** `segments` is a lazy generator. If you try to read `info.language` before iterating, the model hasn't even run yet. Always call `segments = list(segments)` before doing anything else with the result.
2. **Long audio hallucinations:** Without `vad_filter=True`, Whisper hallucinates text in silent sections. Always enable VAD for video content.
3. **CUDA version mismatch:** `ctranslate2` is very specific about CUDA/cuDNN versions. Pin the version explicitly in requirements.txt if targeting GPU.
4. **First-run model download:** Models are downloaded from HuggingFace Hub on first use, which can take minutes. Add a CLI `--download-model` command for explicit initialization.
5. **Thread safety:** `WhisperModel` instances are not thread-safe for concurrent transcription. Use a queue or per-request model instantiation (expensive) for concurrent API use.

### Argos Translate
1. **First-run internet required:** `update_package_index()` fetches a JSON index from argosopentech.com. For offline-first design, bundle the index JSON or pre-install all packages.
2. **Slow first translation:** CTranslate2 loads the model into memory on first call per session — expect 1-5 second delay. Warm up at startup.
3. **Translation quality:** Quality is good for common European language pairs (en↔es/fr/de/pt) but degrades significantly for distant language pairs or languages with limited training data.
4. **Package storage on Windows:** Default paths use `%LOCALAPPDATA%` — ensure write permissions in containerized environments.

### FFmpeg
1. **System dependency:** FFmpeg must be installed separately. Document this clearly in README and provide install instructions per OS.
2. **Temp file cleanup:** Always clean up temp video/audio files in a `finally` block or context manager. Failed transcriptions can leave large temp files.
3. **Sample rate:** Whisper was trained on 16kHz audio. Always extract at `-ar 16000` to avoid internal resampling.

### FastAPI + large files
1. **`SpooledTemporaryFile` has no `.name`:** You cannot pass an `UploadFile.file` path to FFmpeg directly. Always copy to a named temp file first with `shutil.copyfileobj`.
2. **Event loop blocking:** `WhisperModel.transcribe()` is synchronous and CPU/GPU-bound. Calling it inside an `async def` endpoint will block the entire event loop. Use `run_in_executor` or make the endpoint `def` to run in FastAPI's threadpool.
3. **Timeout:** Long videos take minutes to transcribe. HTTP clients will timeout. Use background tasks + polling pattern instead of synchronous response.

### pysrt vs srt
1. **pysrt is unmaintained:** Last release in 2020. Has issues with some edge-case SRT encodings. Prefer the `srt` library.
2. **Timecode arithmetic:** Whisper timestamps are floats in seconds; SRT needs `HH:MM:SS,mmm`. Use `datetime.timedelta` objects, not manual string formatting.

### Stack Combination Specific
1. **Two CTranslate2 users compete for GPU VRAM:** Both faster-whisper and Argos Translate use CTranslate2 under the hood. If both run on GPU simultaneously, VRAM pressure doubles. Consider running translation on CPU (it's much lighter than transcription).
2. **Model loading time at startup:** WhisperModel + Argos model loading combined can take 5-15 seconds. Do both in the lifespan handler, not lazily on first request.

---

## 8. Recommended Project Layout: Models, Temp Files, Output Files

```
# Runtime directories (create at startup, gitignored)
models/whisper/         # auto-downloaded by faster-whisper (configurable via HF_HOME env)
models/argos/           # pre-installed .argosmodel packages
temp/                   # intermediate video/audio during processing
output/                 # final .srt files

# Environment variable pattern
HF_HOME=./models/whisper  # redirect HuggingFace downloads to local dir
ARGOS_TRANSLATE_PACKAGES_DIR=./models/argos  # not a real env var — use install_from_path()
```

### Config Management
Use `pydantic-settings` (part of Pydantic v2) for config:
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    whisper_model: str = "medium"
    whisper_device: str = "cpu"
    temp_dir: str = "./temp"
    output_dir: str = "./output"
    argos_packages_dir: str = "./models/argos"
    
    model_config = {"env_prefix": "GENSUBTITLES_"}
```

### Gitignore Additions
```
models/
temp/
output/
*.srt  # optionally
```

---

## Roadmap Implications

Suggested phase structure based on research:

1. **Core pipeline (CLI)** — audio extraction → transcription → SRT output, no translation. Validates the FFmpeg + faster-whisper + srt integration end-to-end before adding complexity.
2. **Translation layer** — add Argos Translate with programmatic package install/management. Separate phase because package management and quality validation needs its own testing.
3. **FastAPI + Uvicorn layer** — wrap core pipeline with REST endpoints. Use BackgroundTasks + job status polling. Separate from core to keep concerns clean.
4. **Model management UX** — CLI commands for downloading/listing models, progress bars, offline verification.
5. **Production hardening** — temp file cleanup, error handling, Uvicorn deployment config, Docker setup with pre-installed models.

**Phase ordering rationale:**
- CLI-first validates pipeline correctness before adding HTTP complexity
- Translation is optional and can be skipped for v1
- FastAPI layer is thin once core works

**Research flags:**
- Phase 3 (FastAPI): Decide between BackgroundTasks (simple) vs run_in_executor (correct for CPU-bound) before implementing
- Phase 5 (Docker): Argos Translate model pre-packaging in Docker needs specific testing — model paths differ by OS

---

## Dependency Summary

```
# requirements.txt
faster-whisper>=1.2.1
argostranslate>=1.11.0
srt>=3.5.3
fastapi>=0.135.0
uvicorn[standard]>=0.30.0
python-multipart>=0.0.9  # FastAPI file uploads
pydantic-settings>=2.0.0  # config management
typer>=0.12.0  # CLI
```

Note: FFmpeg is a **system dependency** (not pip). Document separately.

---

## Sources

| Topic | Source | Confidence |
|-------|--------|------------|
| faster-whisper | https://github.com/SYSTRAN/faster-whisper (v1.2.1) | HIGH |
| faster-whisper | https://pypi.org/project/faster-whisper/ | HIGH |
| argostranslate | https://github.com/argosopentech/argos-translate (v1.11.0) | HIGH |
| argostranslate | https://pypi.org/project/argostranslate/ | HIGH |
| FastAPI UploadFile | https://fastapi.tiangolo.com/tutorial/request-files/ | HIGH |
| FastAPI BackgroundTasks | https://fastapi.tiangolo.com/tutorial/background-tasks/ | HIGH |
| FastAPI structure | https://fastapi.tiangolo.com/tutorial/bigger-applications/ | HIGH |
| srt library | https://github.com/cdown/srt (v3.5.3) | HIGH |
| srt library | https://pypi.org/project/srt/ | HIGH |
| ffmpeg-python | https://github.com/kkroening/ffmpeg-python | HIGH (negative finding verified) |
| pysrt | https://github.com/byroot/pysrt (v1.1.2) | HIGH (negative finding verified) |
