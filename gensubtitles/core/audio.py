import shutil

if shutil.which("ffmpeg") is None:
    raise EnvironmentError(
        "FFmpeg is not installed or not on PATH. "
        "Install it with:\n"
        "  Linux:   sudo apt install ffmpeg\n"
        "  macOS:   brew install ffmpeg\n"
        "  Windows: winget install ffmpeg"
    )

# Stub — implementation in Phase 2: Audio Extraction Module
