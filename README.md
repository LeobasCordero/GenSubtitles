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

## Quick Start

Pick the usage mode that suits you:

- **GUI (desktop app):** `python main.py gui` — see [GUI Usage](#gui-usage)
- **CLI (command line):** `python main.py --input video.mp4` — see [CLI Usage](#cli-usage)
- **API (REST server):** `python main.py serve` — see [API Usage](#api-usage)

## GUI Usage

### Generating Subtitles

1. Launch the desktop app: `python main.py gui`
2. Click **Browse…** and choose your video file (`.mp4`, `.mkv`, `.avi`, `.mov`, `.webm`).
3. The **Output** path is auto-populated by default after you select a video. You can change it if needed, but it must be set before clicking **Generate**.
4. Set the **Source Language** (leave blank for auto-detection) and optionally set a **Target Language** to enable translation.
5. Click **Generate** to start. Progress steps are shown in the status area.

> **Whisper model:** The GUI does not currently expose a model selector. Model size is controlled by the `WHISPER_MODEL_SIZE` environment variable and defaults to `medium`.
>
> **First run:** The configured Whisper model is downloaded on first use. The default `medium` model is ~1.5 GB. Use `small` (~470 MB) or `tiny` (~75 MB) via `WHISPER_MODEL_SIZE` to reduce the initial download.

### Translation Settings

Use the **Source Language** and **Target Language** dropdowns on the main form to control translation:

- Leave **Source Language** blank to let Whisper auto-detect the spoken language.
- Set **Target Language** to an ISO 639-1 code (e.g., `es` for Spanish, `fr` for French) to translate subtitles after transcription.
- Leave **Target Language** blank to skip translation and output in the source language.

Translation in the GUI uses **Argos Translate** by default (offline, no API key required). Argos models for each language pair are downloaded on first use (~50–200 MB each) and cached locally.

> **Note:** The GUI can also use **DeepL** and **LibreTranslate** when they are configured. DeepL is available after setting `deepl_api_key`, and LibreTranslate is available after setting `libretranslate_url`. You can also select these engines via CLI with `--engine deepl` or `--engine libretranslate`.

### Configuring the App (Settings Dialog)

Open the Settings dialog from the **Settings** button or the app menu to configure application-wide preferences. Changes are saved automatically to `settings.json` (see [Configuration](#configuration)).

| Setting | Options | Default |
|---------|---------|---------|
| `appearance_mode` | `Light`, `Dark`, `System` | `System` |
| `ui_language` | `en`, `es` | `en` |
| `default_output_dir` | Absolute path, or blank (same dir as input) | _(blank)_ |
| `default_source_lang` | ISO 639-1 code, or blank (auto-detect) | _(blank)_ |
| `target_lang` | ISO 639-1 code, or blank (no translation) | _(blank)_ |
| `deepl_api_key` | Free-tier key from [deepl.com](https://deepl.com) | _(blank)_ |
| `libretranslate_url` | e.g., `http://localhost:5000` | _(blank)_ |
| `libretranslate_api_key` | Blank for open instances | _(blank)_ |

### Help Menu

The **Help** menu in the menu bar provides:

- **Installed Language Pairs** — Lists all Argos Translate models currently downloaded and ready for offline use. Open this to check which language pairs are available before generating subtitles.
- **Tutorial** — Opens a quick-start guide.
- **About** — Shows the application version and license information.

## CLI Usage

> For a full step-by-step walkthrough, see [CLI Tutorial](docs/cli-tutorial.md).

### generate (default)

```bash
python main.py --input video.mp4 [OPTIONS]
```

Generates subtitles from a video file and writes an `.srt` or `.ssa` file.

| Flag | Description | Default |
|------|-------------|---------|
| `--input`, `-i` | Input video (`.mp4`, `.mkv`, `.avi`, `.mov`, `.webm`) | Required |
| `--output`, `-o` | Destination subtitle path | `<input>.<format>` |
| `--model`, `-m` | Whisper model: `tiny` / `base` / `small` / `medium` / `large-v1` / `large-v2` / `large-v3` / `turbo` | `medium` |
| `--target-lang`, `-t` | ISO 639-1 target language code (e.g., `es`). Omit = no translation | None |
| `--source-lang`, `-s` | Source language code. Omit = Whisper auto-detect | Auto |
| `--device` | Compute device: `auto` / `cpu` / `cuda` | `auto` |
| `--format`, `-f` | Output format: `srt` or `ssa` | `srt` |
| `--engine` | Translation engine: `argos` (offline default) / `deepl` / `libretranslate` | `argos` |

**Examples:**
```bash
# Basic — generates subtitles.srt in same directory as input
python main.py --input video.mp4

# With translation to Spanish
python main.py --input video.mp4 --target-lang es

# SSA output using DeepL
python main.py --input video.mp4 --target-lang fr --format ssa --engine deepl

# Smaller model on CPU
python main.py --input video.mp4 --model small --device cpu
```

> **First run:** The `medium` model requires a one-time ~1.5 GB download. Use `--model small` (~470 MB) or `--model tiny` (~75 MB) for a smaller initial download.

### translate

```bash
python main.py translate <file> --target-lang <code> [OPTIONS]
```

Translates an existing `.srt` or `.ssa` subtitle file without re-transcribing.

| Argument / Flag | Description | Default |
|-----------------|-------------|---------|
| `<file>` | Input subtitle file (`.srt` or `.ssa`) | Required |
| `--target-lang`, `-t` | Target ISO 639-1 language code | Required |
| `--source-lang`, `-s` | Source language code | `en` |
| `--output`, `-o` | Output path | `<input>_translated.<ext>` |

**Example:**
```bash
python main.py translate subtitles.srt --target-lang es
```

### convert

```bash
python main.py convert <input> <output>
```

Converts a subtitle file between formats (`.srt` ↔ `.ssa`). The output format is inferred from the output file extension.

**Example:**
```bash
python main.py convert subtitles.srt subtitles.ssa
```

### serve

```bash
python main.py serve [--host HOST] [--port PORT] [--reload]
```

Starts the GenSubtitles FastAPI REST API server.

| Flag | Description | Default |
|------|-------------|---------|
| `--host` | Host address to bind to | `127.0.0.1` |
| `--port` | Port to listen on | `8000` |
| `--reload` | Enable auto-reload (development mode) | `false` |

**Example:**
```bash
# Expose on all interfaces
python main.py serve --host 0.0.0.0 --port 8000
```

## API Usage

GenSubtitles provides a REST API powered by FastAPI.

**Start the server:**
```bash
python main.py serve
```

Or using uvicorn directly:
```bash
uvicorn gensubtitles.api.main:app --host 0.0.0.0 --port 8000
```

### POST /subtitles

Upload a video file and receive a subtitle file in response.

**Basic example:**
```bash
curl -X POST http://localhost:8000/subtitles \
  -F "file=@video.mp4" \
  --output subtitles.srt
```

**With translation:**
```bash
curl -X POST "http://localhost:8000/subtitles?target_lang=es" \
  -F "file=@video.mp4" \
  --output subtitles.srt
```

**Query parameters:**
- `target_lang` (optional): ISO 639-1 target language code for translation
- `source_lang` (optional): Force source language (omit for auto-detect)
- `engine` (optional): Translation engine to use (`argos`, `deepl`, or `libretranslate`)

### Interactive API documentation

FastAPI provides interactive documentation at:
```
http://localhost:8000/docs
```

## Configuration

Settings are stored as JSON at:
- **Linux:** `~/.config/GenSubtitles/settings.json`
- **macOS:** `~/Library/Application Support/GenSubtitles/settings.json`
- **Windows:** `%APPDATA%\GenSubtitles\settings.json`

The file is created when settings are saved for the first time (e.g., from the GUI Settings dialog), so it may not exist yet on first launch. You can edit it directly once it exists or use the Settings dialog in the GUI.

### Settings fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `appearance_mode` | string | `"System"` | UI theme: `"Light"`, `"Dark"`, or `"System"` |
| `ui_language` | string | `"en"` | Interface language: `"en"` or `"es"` |
| `default_output_dir` | string | `""` | Default output directory. Empty = same directory as the input video |
| `default_source_lang` | string | `""` | Default source language (ISO 639-1). Empty = Whisper auto-detect |
| `target_lang` | string | `""` | Default target language for translation. Empty = no translation |
| `deepl_api_key` | string | `""` | DeepL Free API key (required to use `--engine deepl`) |
| `libretranslate_url` | string | `""` | LibreTranslate server URL (e.g., `"http://localhost:5000"`) |
| `libretranslate_api_key` | string | `""` | LibreTranslate API key. Empty = open instance |

## Troubleshooting

### FFmpeg not found

**Error:**
```
EnvironmentError: FFmpeg not found in PATH
```

**Solution:** Install FFmpeg using the commands in the Installation section above. After installation, verify with `ffmpeg -version` and restart your terminal to refresh the PATH.

### Argos model download failure

**Error:** Network timeout or HTTP error during model download.

**Solution:** Check your internet connection and retry. Language models are downloaded once on first use and cached locally. If failures persist, try again on a stable connection.

### Missing output directory

**Error:** `FileNotFoundError` or permission errors when writing the subtitle file.

**Solution:** Ensure the output directory exists and is writable. Use `--output` to specify a valid path:
```bash
python main.py --input video.mp4 --output /path/to/writable/directory/subtitles.srt
```

### DeepL / LibreTranslate not working

The GUI supports DeepL and LibreTranslate when they are properly configured. If these engines are not working, check the following:

- **DeepL:** Ensure `deepl_api_key` is set in the Settings dialog or `settings.json`. A valid [DeepL Free API key](https://deepl.com) is required.
- **LibreTranslate:** Ensure `libretranslate_url` is set to a reachable server (e.g., `http://localhost:5000`). Check that the server is running and accessible.
- **Network errors:** Both engines require network connectivity. Verify your internet connection and firewall settings.

You can also use these engines via CLI:
```bash
python main.py --input video.mp4 --target-lang es --engine deepl
python main.py --input video.mp4 --target-lang es --engine libretranslate
```

### First run — large model download

The default `medium` model requires a ~1.5 GB one-time download. Use a smaller model to reduce the initial download:
```bash
python main.py --input video.mp4 --model small   # ~470 MB
python main.py --input video.mp4 --model tiny    # ~75 MB
```

## License

MIT
