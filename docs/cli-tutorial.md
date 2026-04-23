# GenSubtitles — CLI Tutorial

> **GUI user?** Open the desktop app with `python main.py gui` instead.

A step-by-step walkthrough of the GenSubtitles command-line interface. Covers every command from first run through advanced pipeline control.

## Prerequisites

**Python ≥ 3.11:**
```bash
python --version
```

**FFmpeg** (required for audio extraction):
```bash
# Linux (Debian/Ubuntu)
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows
winget install --id Gyan.FFmpeg

# Verify
ffmpeg -version
```

**Install GenSubtitles:**
```bash
# Recommended — uses uv lockfile
uv sync

# Or with pip
pip install -r requirements.txt
```

> For full installation details see the [README](../README.md#installation).

## 1. Generate Subtitles (`generate`)

The default command — takes a video file and writes a subtitle file.

### Basic transcription

```bash
# Generates video.srt in the same directory as the input
python main.py --input video.mp4
```

Expected output:
```
[1/4] Extracting audio...
[2/4] Transcribing...
[3/4] Writing SRT...
[4/4] Writing SRT...
Done: video.srt (42 segments, lang=en)
```

### With translation

```bash
# Transcribe and translate to Spanish
python main.py --input video.mp4 --target-lang es

# Specify source language explicitly (skip Whisper auto-detect)
python main.py --input video.mp4 --target-lang fr --source-lang en
```

Expected output with translation:
```
[1/4] Extracting audio...
[2/4] Transcribing...
[3/4] Translating...
[4/4] Writing SRT...
Done: video.srt (42 segments, lang=en)
```

### Custom output path

```bash
python main.py --input video.mp4 --output /path/to/my-subtitles.srt
```

### Format options

```bash
# SSA format (richer styling — supported by VLC, mpv, Aegisub)
python main.py --input video.mp4 --format ssa

# SSA + translation
python main.py --input video.mp4 --target-lang es --format ssa
```

SRT is the most widely compatible format. Use SSA when your player supports advanced subtitle styling.

### Engine selection

```bash
# Argos Translate — fully offline (default)
python main.py --input video.mp4 --target-lang es --engine argos

# DeepL — higher quality, requires DEEPL_API_KEY env var
python main.py --input video.mp4 --target-lang es --engine deepl

# LibreTranslate — self-hosted, requires LIBRETRANSLATE_URL env var
python main.py --input video.mp4 --target-lang es --engine libretranslate
```

See [Translation Engines](#7-translation-engines) for a comparison.

### Full flag reference

| Flag | Description | Default |
|------|-------------|---------|
| `--input`, `-i` | Input video (`.mp4`, `.mkv`, `.avi`, `.mov`, `.webm`) | Required |
| `--output`, `-o` | Destination subtitle path | `<input>.<format>` |
| `--model`, `-m` | Whisper model size | `medium` |
| `--target-lang`, `-t` | ISO 639-1 target language code (e.g., `es`). Omit = no translation | None |
| `--source-lang`, `-s` | Source language code. Omit = Whisper auto-detect | Auto |
| `--device` | Compute device: `auto` / `cpu` / `cuda` | `auto` |
| `--format`, `-f` | Output format: `srt` or `ssa` | `srt` |
| `--engine` | Translation engine: `argos` / `deepl` / `libretranslate` | `argos` |

## 2. Translate an Existing Subtitle File (`translate`)

If you already have an `.srt` or `.ssa` file and only need to translate it:

```bash
# Translate subtitles.srt to Spanish (defaults to English as source)
python main.py translate subtitles.srt --target-lang es

# Specify the source language explicitly
python main.py translate subtitles.srt --target-lang de --source-lang fr

# Custom output path (default: subtitles_translated.srt)
python main.py translate subtitles.srt --target-lang es --output subtitles_es.srt
```

Expected output:
```
Done: subtitles_translated.srt
```

## 3. Convert Format (`convert`)

Convert between `.srt` and `.ssa` without re-transcribing or translating:

```bash
# SRT to SSA
python main.py convert subtitles.srt subtitles.ssa

# SSA to SRT
python main.py convert subtitles.ssa subtitles.srt
```

Expected output:
```
Done: subtitles.ssa
```

The output format is inferred from the output file extension.

## 4. Start the API Server (`serve`)

Start the GenSubtitles FastAPI REST server:

```bash
# Default: localhost:8000
python main.py serve

# Expose on all network interfaces
python main.py serve --host 0.0.0.0 --port 8000

# Development mode (auto-reload on code changes)
python main.py serve --reload
```

Expected output:
```
Starting GenSubtitles API on http://127.0.0.1:8000 ...
```

### Generating subtitles via the API

Once the server is running, submit a video with `curl`:

```bash
# Basic — returns subtitles.srt
curl -X POST http://localhost:8000/subtitles \
  -F "file=@video.mp4" \
  --output subtitles.srt

# With translation to Spanish
curl -X POST "http://localhost:8000/subtitles?target_lang=es" \
  -F "file=@video.mp4" \
  --output subtitles_es.srt

# SSA format + DeepL engine
curl -X POST "http://localhost:8000/subtitles?target_lang=fr&format=ssa&engine=deepl" \
  -F "file=@video.mp4" \
  --output subtitles.ssa
```

> Interactive API docs are available at `http://localhost:8000/docs` while the server is running.

## 5. The `--step` Stepper

The `--step` flag runs a single pipeline stage at a time, storing intermediate files in a work directory. Use it to debug a specific stage, resume a failed run, or run stages on different machines.

The four stages in order: `extract` → `transcribe` → `translate` → `write`

### Full 4-stage walkthrough

**Stage 1 — Extract audio from the video:**

```bash
python main.py --input video.mp4 --step extract --work-dir ./my-job/
```
```
[1/4] Extracting audio...
Done: my-job\audio.wav
```

**Stage 2 — Transcribe the audio:**

```bash
python main.py --step transcribe --work-dir ./my-job/
```
```
[2/4] Transcribing...
Done: my-job\transcription.json (42 segments, lang=en)
```

**Stage 3 — Translate the transcription:**

```bash
python main.py --step translate --work-dir ./my-job/ --target-lang es
```
```
[3/4] Translating...
Done: my-job\translation.json
```

**Stage 4 — Write the subtitle file:**

```bash
python main.py --step write --work-dir ./my-job/ --output final.srt
```
```
[4/4] Writing SRT...
Done: final.srt
```

### Stage options

| Stage | Required flags | Optional flags |
|-------|----------------|----------------|
| `extract` | `--input`, `--work-dir` | — |
| `transcribe` | `--work-dir` | `--model`, `--source-lang`, `--device` |
| `translate` | `--work-dir`, `--target-lang` | `--engine` |
| `write` | `--work-dir` | `--output`, `--format` |

## 6. Model Comparison

| Model | Download size | Use when |
|-------|---------------|----------|
| `tiny` | ~75 MB | Fastest; good for quick tests or short clips with clear speech |
| `base` | ~145 MB | Good balance for simple content |
| `small` | ~470 MB | Better accuracy for conversational speech |
| `medium` | ~1.5 GB | **Default.** Solid accuracy for most content |
| `large-v1` / `large-v2` / `large-v3` | ~3 GB | Most accurate; best for difficult accents or technical vocabulary |
| `turbo` | ~810 MB | Near-large accuracy at medium speed |

> **First run:** The selected model downloads automatically (internet required for the download only). All subsequent runs are fully offline.

## 7. Translation Engines

| Engine | Mode | Use when |
|--------|------|----------|
| `argos` | Fully offline (default) | Privacy matters or no internet; good quality for common language pairs |
| `deepl` | Cloud API | Highest quality; requires `DEEPL_API_KEY` environment variable |
| `libretranslate` | Self-hosted | Own infrastructure; requires `LIBRETRANSLATE_URL` environment variable |

## 8. Quick Reference

```bash
python main.py --input video.mp4                                         # transcribe only
python main.py --input video.mp4 --target-lang es                        # transcribe + translate
python main.py --input video.mp4 --model small                           # faster/smaller model
python main.py --input video.mp4 --format ssa                            # SSA output
python main.py --input video.mp4 --target-lang es --engine deepl         # DeepL translation
python main.py translate subs.srt --target-lang fr                       # translate existing file
python main.py convert subs.srt subs.ssa                                 # convert format
python main.py serve                                                      # start API server
python main.py --input video.mp4 --step extract --work-dir ./my-job/     # stepper mode
```

> **Prefer a graphical interface?** Run `python main.py gui` to open the desktop app.
> The GUI Tutorial (Help > Tutorial) covers all GUI features step by step.
