"""
gensubtitles.core.audio
~~~~~~~~~~~~~~~~~~~~~~~
FFmpeg-based audio extraction from video files.

Provides:
    extract_audio(video_path, output_path) -> None
        Extract audio track as 16kHz mono WAV.

    audio_temp_context(suffix=".wav") -> Generator[Path, None, None]
        Context manager for temp WAV files — auto-deleted on exit.
"""
import os
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from gensubtitles.exceptions import AudioExtractionError

# ---------------------------------------------------------------------------
# Import-time FFmpeg availability check (D-05)
# Fail fast before any pipeline runs — surfaces a clear install message.
# ---------------------------------------------------------------------------
if shutil.which("ffmpeg") is None:
    raise EnvironmentError(
        "FFmpeg is not installed or not on PATH. "
        "Install it with:\n"
        "  Linux:   sudo apt install ffmpeg\n"
        "  macOS:   brew install ffmpeg\n"
        "  Windows: winget install ffmpeg"
    )

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(
    {".mp4", ".mkv", ".avi", ".mov", ".webm"}
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_audio(video_path: str | Path, output_path: str | Path) -> None:
    """
    Extract the audio track from a video file to a 16kHz mono WAV file.

    Args:
        video_path:  Path to the input video file. Must have a supported
                     extension: .mp4, .mkv, .avi, .mov, .webm
        output_path: Path where the output WAV file will be written.
                     Existing file is overwritten silently.

    Raises:
        ValueError:             If the file extension is not in SUPPORTED_EXTENSIONS.
        AudioExtractionError:   If FFmpeg exits with a non-zero return code
                                (includes "no audio track" condition).
    """
    video_path = Path(video_path)
    output_path = Path(output_path)

    # --- AUD-01: validate extension before any subprocess ---
    ext = video_path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported video format '{ext}'. "
            f"Supported formats: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    # --- AUD-02: build FFmpeg command ---
    # -hide_banner : suppress version/build info banner
    # -loglevel error: suppress progress stats; only emit errors to stderr
    # -vn      : disable video output (audio-only extraction)
    # -ar 16000: resample to 16 kHz (Whisper's native sample rate)
    # -ac 1    : mono channel
    # -f wav   : force WAV container
    # -y       : overwrite output without prompting
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "error",
        "-i", str(video_path),
        "-vn",
        "-ar", "16000",
        "-ac", "1",
        "-f", "wav",
        "-y",
        str(output_path),
    ]

    result = subprocess.run(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    # --- AUD-02 / AUD-03: raise on failure ---
    if result.returncode != 0:
        raise AudioExtractionError(
            f"FFmpeg failed (exit {result.returncode}):\n{result.stderr}"
        )


@contextmanager
def audio_temp_context(suffix: str = ".wav") -> Generator[Path, None, None]:
    """
    Context manager that creates a temporary audio file, yields its Path,
    and deletes it on exit — whether the block completes normally or raises.

    Usage:
        with audio_temp_context() as tmp_wav:
            extract_audio(video_path, tmp_wav)
            process(tmp_wav)
        # tmp_wav is deleted here — AUD-04

    Args:
        suffix: File suffix for the temp file. Defaults to ".wav".

    Yields:
        pathlib.Path pointing at the (initially empty) temp file.
    """
    # mkstemp returns (fd, path_str) — fd is an open file descriptor
    fd, path_str = tempfile.mkstemp(suffix=suffix)
    tmp_path = Path(path_str)
    try:
        # Close the fd immediately so FFmpeg can write to the path on Windows
        os.close(fd)
        yield tmp_path
    finally:
        # AUD-04: always clean up — missing_ok=True handles the case where
        # the caller never wrote to the file (e.g., early exception)
        tmp_path.unlink(missing_ok=True)
