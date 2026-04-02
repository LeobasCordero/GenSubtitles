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
```powershell
winget install ffmpeg
```

Verify: `ffmpeg -version`

### 2. Python dependencies

**Primary (recommended):**
```bash
uv sync
```

**Pip fallback:**
```bash
pip install -r requirements.txt
```

Requires Python ≥ 3.11.

## CLI Usage

```bash
python main.py --input video.mp4 --output subtitles.srt
```

## API Usage

```bash
# Coming in Phase 8
```

## License

MIT
