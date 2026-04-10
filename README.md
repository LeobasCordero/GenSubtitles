# GenSubtitles

Automatic video subtitle generation — offline, no API keys required. Transcribes and optionally translates video audio using Whisper and Argos Translate.

## Installation

### 1. System dependency: FFmpeg

FFmpeg must be installed before running GenSubtitles.

**Linux (Debian/Ubuntu):**
```bash
sudo apt install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
```bash
winget install --id Gyan.FFmpeg
```

Verify installation:
```bash
ffmpeg -version
```

### 2. Python dependencies

**Using uv (recommended):**
```bash
uv sync
```

**Using pip:**
```bash
pip install -r requirements.txt
```

Requires Python ≥ 3.11.

## CLI Usage

GenSubtitles provides a command-line interface with 6 configurable flags.

**Basic usage (auto-detects output path):**
```bash
python main.py --input video.mp4
```

**Custom output path:**
```bash
python main.py --input video.mp4 --output subtitles.srt
```

**With translation to Spanish:**
```bash
python main.py --input video.mp4 --target-lang es
```

**Custom model and device:**
```bash
python main.py --input video.mp4 --model base --device cpu
```

### Available Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--input`, `-i` | Path to input video file (`.mp4`, `.mkv`, `.avi`, `.mov`, `.webm`) | Required |
| `--output`, `-o` | Destination `.srt` path | `<input>.srt` |
| `--model`, `-m` | Whisper model size: `tiny`, `base`, `small`, `medium`, `large-v1`, `large-v2`, `large-v3`, `turbo` | `small` |
| `--target-lang`, `-t` | Target ISO 639-1 language code for translation (e.g., `es`, `fr`, `de`) | None (no translation) |
| `--source-lang`, `-s` | Source language code (omit for auto-detection) | Auto-detect |
| `--device` | Compute device: `auto`, `cpu`, `cuda` | `auto` |

For full options:
```bash
python main.py --help
```

## API Usage

GenSubtitles provides a REST API powered by FastAPI.

### Starting the server

**Using the main entry point:**
```bash
python main.py serve
```

**Using uvicorn directly:**
```bash
uvicorn gensubtitles.api.main:app --host 0.0.0.0 --port 8000
```

### Endpoints

#### POST /subtitles

Upload a video file and receive an SRT subtitle file in response.

**Basic example:**
```bash
curl -X POST http://localhost:8000/subtitles \
  -F "file=@video.mp4" \
  --output subtitles.srt
```

**With translation:**
```bash
curl -X POST http://localhost:8000/subtitles \
  -F "file=@video.mp4" \
  -F "target_lang=es" \
  --output subtitles.srt
```

**Query parameters:**
- `target_lang` (optional): ISO 639-1 target language code for translation
- `source_lang` (optional): Force source language detection (omit for auto-detect)

#### Interactive API documentation

FastAPI provides interactive API documentation at:
```
http://localhost:8000/docs
```

## Language Translation

GenSubtitles uses Argos Translate for multilingual subtitle generation.

**First-time model download:**
- On first use of a language pair (e.g., English → Spanish), Argos Translate downloads the required model (~50-200 MB depending on language pair)
- Models are downloaded from the internet — first translation requires network connectivity
- Downloaded models are cached locally in the OS-appropriate cache directory

**Subsequent runs:**
- After the initial download, all translation runs are fully offline
- Models remain cached across sessions

**Supported languages:**
Use ISO 639-1 codes with the `--target-lang` flag (e.g., `es` for Spanish, `fr` for French, `de` for German, `pt` for Portuguese).

## Troubleshooting

### FFmpeg not found

**Error:**
```
EnvironmentError: FFmpeg not found in PATH
```

**Solution:**
Install FFmpeg using the commands in the Installation section above. After installation, verify with `ffmpeg -version` and restart your terminal to refresh the PATH.

### Argos model download failure

**Error:**
Network timeout or HTTP error during model download.

**Solution:**
Check your internet connection and retry the command. Language models download once on first use and are cached locally. If download failures persist, try again with a stable network connection.

### Missing output directory

**Error:**
```
FileNotFoundError
```
or permission errors when writing the SRT file.

**Solution:**
Ensure the output directory exists and is writable. You can use the `--output` flag to specify a valid path:
```bash
python main.py --input video.mp4 --output /path/to/writable/directory/subtitles.srt
```

## License

MIT
