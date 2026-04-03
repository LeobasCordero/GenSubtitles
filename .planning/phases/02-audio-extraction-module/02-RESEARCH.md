# Phase 2: Audio Extraction Module — Research

**Phase:** 02 — Audio Extraction Module  
**Requirements:** AUD-01, AUD-02, AUD-03, AUD-04  
**Researched:** 2026-04-02

---

## Summary

Phase 2 is a well-bounded subprocess + file I/O problem. No external API, no novel library. The research below consolidates the authoritative patterns for FFmpeg subprocess calls, Python tempfile management, exception design, and pytest fixture strategy. All decisions from CONTEXT.md are confirmed compatible with Python 3.11+ stdlib.

---

## 1. FFmpeg Subprocess Command

### Exact command
```python
["ffmpeg", "-i", str(video_path), "-vn", "-ar", "16000", "-ac", "1", "-f", "wav", "-y", str(output_path)]
```

| Flag | Purpose |
|------|---------|
| `-i <path>` | Input file |
| `-vn` | Disable video stream output (audio-only) |
| `-ar 16000` | Resample to 16 kHz (Whisper's native sample rate) |
| `-ac 1` | Mono channel (halves data, Whisper doesn't use stereo) |
| `-f wav` | Force WAV container |
| `-y` | Overwrite output if exists (idempotent) |

### subprocess.run call pattern
```python
result = subprocess.run(
    cmd,
    capture_output=True,
    text=True,          # decode stdout/stderr as str
    check=False,        # we inspect returncode manually
)
if result.returncode != 0:
    raise AudioExtractionError(
        f"FFmpeg failed (exit {result.returncode}):\n{result.stderr}"
    )
```

**Why `check=False`:** `check=True` raises `subprocess.CalledProcessError` — we want to raise our own `AudioExtractionError`. `check=False` gives us control.

**Why `capture_output=True`:** Suppresses FFmpeg's noisy progress output to the terminal. Stderr is captured and surfaced in the exception message only on failure.

**Why `text=True`:** FFmpeg stderr is UTF-8 text. Decoding here avoids `result.stderr.decode()` calls downstream.

### No timeout (YAGNI per D-06)
Timeout deferred — not in scope for this phase. Can add `timeout=300` parameter in a future phase.

---

## 2. Input Validation

### Supported extensions (AUD-01)
```python
SUPPORTED_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm"}
```

### Validation pattern
```python
ext = Path(video_path).suffix.lower()
if ext not in SUPPORTED_EXTENSIONS:
    raise ValueError(
        f"Unsupported video format '{ext}'. "
        f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
    )
```

**Why `.lower()`:** Windows is case-insensitive; `.MP4` and `.mp4` are the same file. Always normalize.

**Why before subprocess:** Fail-fast. Extension check is O(1); no FFmpeg process needed to detect a bad extension.

---

## 3. Exception Design — `gensubtitles/exceptions.py`

### Module structure
```python
# gensubtitles/exceptions.py

class GenSubtitlesError(RuntimeError):
    """Base exception for all GenSubtitles errors."""

class AudioExtractionError(GenSubtitlesError):
    """
    Raised when FFmpeg fails to extract audio from a video file.

    Attributes:
        message: Human-readable error description (includes FFmpeg stderr on failure).
    """
```

**Why a base class `GenSubtitlesError`:** Downstream catch blocks (pipeline, CLI, API) can catch all project errors with `except GenSubtitlesError` without importing each specific class. Future modules (TranscriptionError, TranslationError) extend the same base — consistent and extensible.

**How to satisfy the `RuntimeError` contract cleanly:** If CONTEXT.md D-01 requires `AudioExtractionError` to be a `RuntimeError` subclass, then `RuntimeError` must appear in its inheritance chain. The shipped implementation defines `GenSubtitlesError(RuntimeError)` as the shared base, with `AudioExtractionError(GenSubtitlesError)` beneath it. This satisfies D-01 strictly while preserving a project-wide catch-all hierarchy. Future modules (`TranscriptionError`, `TranslationError`) extend the same base — consistent and extensible.

> **Note for planner:** CONTEXT.md D-01 says `AudioExtractionError(RuntimeError)`. The implementation uses `GenSubtitlesError(RuntimeError)` as an intermediate base, with `AudioExtractionError(GenSubtitlesError)` beneath it — this satisfies strict D-01 compliance and provides a shared project exception hierarchy.

---

## 4. Temp-File Context Manager

### `tempfile.mkstemp()` pattern
```python
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

@contextmanager
def audio_temp_context(suffix: str = ".wav") -> Generator[Path, None, None]:
    """
    Context manager that creates a temporary WAV file, yields its Path,
    and deletes it on exit (even if an exception is raised).
    """
    fd, path_str = tempfile.mkstemp(suffix=suffix)
    tmp_path = Path(path_str)
    try:
        os.close(fd)          # Close the file descriptor immediately
        yield tmp_path        # Caller uses this path with FFmpeg
    finally:
        tmp_path.unlink(missing_ok=True)  # Cleanup on success or exception
```

**Why `os.close(fd)` before yield:** `mkstemp` opens the file and returns an open fd. If we yield without closing, FFmpeg's write to the same path on Windows will fail with a "file in use" error. Close the fd first, let FFmpeg own the file.

**Why `missing_ok=True`:** If FFmpeg never wrote the file (e.g., validation raised before FFmpeg ran), `unlink()` without `missing_ok=True` raises `FileNotFoundError`. `missing_ok=True` handles this cleanly.

**Why `suffix=".wav"`:** `mkstemp` uses the suffix for the extension; FFmpeg determines format by the `-f wav` flag, but having `.wav` in the filename is good practice for downstream tools that use the extension as a hint.

---

## 5. `extract_audio` Function Signature and Flow

```python
def extract_audio(video_path: str | Path, output_path: str | Path) -> None:
    """
    Extract audio from a video file to a 16kHz mono WAV file.

    Args:
        video_path: Path to the input video file.
        output_path: Path where the output WAV file will be written.

    Raises:
        ValueError: If the video file extension is not supported.
        AudioExtractionError: If FFmpeg fails (non-zero exit code).
    """
    video_path = Path(video_path)
    output_path = Path(output_path)

    # 1. Validate extension
    ext = video_path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(...)

    # 2. Build and run FFmpeg command
    cmd = ["ffmpeg", "-i", str(video_path), "-vn", "-ar", "16000",
           "-ac", "1", "-f", "wav", "-y", str(output_path)]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)

    # 3. Check for failure
    if result.returncode != 0:
        raise AudioExtractionError(f"FFmpeg failed (exit {result.returncode}):\n{result.stderr}")
```

**Accept `str | Path`:** CLI and API callers will pass strings; typed callers will pass `Path`. Convert at entry — don't force callers to manage types.

---

## 6. Testing Strategy

### `conftest.py` session-scoped fixture

The `lavfi` virtual device in FFmpeg generates audio/video from mathematical functions — no input file needed, completely deterministic.

```python
# tests/conftest.py
import subprocess
import tempfile
import os
import pytest
from pathlib import Path


@pytest.fixture(scope="session")
def synthetic_video(tmp_path_factory) -> Path:
    """
    Session-scoped fixture: generate a 1-second synthetic mp4 with audio via FFmpeg.
    Reused across all tests in the session — generated only once.
    """
    tmp_dir = tmp_path_factory.mktemp("fixtures")
    output = tmp_dir / "test_video.mp4"
    result = subprocess.run(
        [
            "ffmpeg",
            "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=25",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
            "-c:v", "libx264", "-c:a", "aac",
            "-shortest",
            str(output),
        ],
        capture_output=True,
        check=True,
    )
    return output
```

### FFmpeg lavfi sources used
| Source | What it generates |
|--------|-----------------|
| `testsrc=duration=1:size=320x240:rate=25` | 1-second color-bar test video, 320×240, 25fps |
| `sine=frequency=440:duration=1` | 1-second 440Hz sine wave (pure tone, silence-free) |

**Why `sine` not `aevalsrc=0`:** `aevalsrc=0` generates silence — Whisper's VAD filter (Phase 3) would suppress it. `sine=440` generates actual audio signal, testing real extraction behavior.

**Why `-shortest`:** The two lavfi inputs both produce exactly 1 second, but `-shortest` ensures the output stops at the shortest stream's end rather than padding.

### Test cases for `test_audio.py`

| Test | AUD req | What it verifies |
|------|---------|----------------|
| `test_extract_audio_creates_wav` | AUD-02 | WAV created, readable by `wave.open()`, framerate=16000, channels=1 |
| `test_extract_audio_output_path_respected` | AUD-02 | Output written to the exact path provided |
| `test_extract_audio_unsupported_extension` | AUD-01 | `ValueError` before FFmpeg spawn |
| `test_extract_audio_temp_context_cleanup` | AUD-04 | Temp file deleted after context exits |
| `test_extract_audio_temp_context_cleanup_on_exception` | AUD-04 | Temp file deleted even when extraction raises |

### WAV validation using stdlib `wave`
```python
import wave

with wave.open(str(output_wav), "rb") as wf:
    assert wf.getframerate() == 16000   # AUD-02: 16kHz
    assert wf.getnchannels() == 1       # AUD-02: mono
    assert wf.getnframes() > 0          # Non-empty audio
```

**Why `wave` module:** Stdlib, no deps, reads WAV header without decoding all audio data — fast and authoritative.

### Testing missing audio track (AUD-03)
The lavfi `testsrc` source has no audio when used alone. To test missing audio:
```python
# Generate a silent video with no audio stream
result = subprocess.run(
    ["ffmpeg", "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=25",
     "-an",  # No audio
     str(silent_video)],
    capture_output=True, check=True
)
```
Then call `extract_audio(silent_video, ...)` and assert `AudioExtractionError` is raised.

> **Note:** FFmpeg with `-vn` on a video that has no audio stream returns non-zero exit code with stderr containing "Output file does not contain any stream" or similar. The catch-all `AudioExtractionError` covers this correctly.

---

## 7. Module Import Order in `core/audio.py`

The Phase 1 stub already has the import-time check. The full module import order should be:

```python
import os
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from gensubtitles.exceptions import AudioExtractionError

# --- Import-time FFmpeg check (D-05) ---
if shutil.which("ffmpeg") is None:
    raise EnvironmentError(
        "FFmpeg is not installed or not on PATH. "
        "Install it with:\n"
        "  Linux:   sudo apt install ffmpeg\n"
        "  macOS:   brew install ffmpeg\n"
        "  Windows: winget install ffmpeg"
    )

SUPPORTED_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm"}
```

**Important:** The import-time FFmpeg check must come AFTER the `from gensubtitles.exceptions import AudioExtractionError` import (circular import risk if check runs before exceptions module is loaded). Since `exceptions.py` has no imports from `gensubtitles`, this is safe.

---

## 8. Validation Architecture

### Test commands
```bash
# Run all audio tests
pytest tests/test_audio.py -v

# Run infrastructure + audio tests together
pytest tests/ -v

# Quick smoke test (extract from synthetic video)
python -c "
from gensubtitles.core.audio import extract_audio, audio_temp_context
# Uses session fixture logic inline
"
```

### Verification checklist (for PLAN.md `<verify>` fields)

| Check | Command |
|-------|---------|
| `exceptions.py` exists with `AudioExtractionError` | `grep "AudioExtractionError" gensubtitles/exceptions.py` |
| `audio.py` imports `AudioExtractionError` | `grep "from gensubtitles.exceptions import" gensubtitles/core/audio.py` |
| `audio.py` has `extract_audio` function | `grep "def extract_audio" gensubtitles/core/audio.py` |
| `audio.py` has `audio_temp_context` | `grep "def audio_temp_context" gensubtitles/core/audio.py` |
| `conftest.py` has session fixture | `grep "scope.*session" tests/conftest.py` |
| AUD-02 — 16kHz mono output | `pytest tests/test_audio.py::test_extract_audio_creates_wav -v` |
| AUD-04 — cleanup on exit | `pytest tests/test_audio.py::test_extract_audio_temp_context_cleanup -v` |
| All audio tests pass | `pytest tests/test_audio.py -v` |

---

## 9. Files Created / Modified

| File | Action | Notes |
|------|--------|-------|
| `gensubtitles/exceptions.py` | **Create** | `GenSubtitlesError` base + `AudioExtractionError` |
| `gensubtitles/core/audio.py` | **Modify** | Implement below stub comment; keep import-time check |
| `tests/conftest.py` | **Create** | Session-scoped synthetic video fixture |
| `tests/test_audio.py` | **Create** | 5 test cases covering AUD-01–AUD-04 |

---

## 10. Common Pitfalls

| Pitfall | Mitigation |
|---------|-----------|
| `mkstemp` fd left open — FFmpeg can't overwrite on Windows | `os.close(fd)` immediately before yielding |
| `AudioExtractionError` imported in `exceptions.py` before it's defined | Define `GenSubtitlesError` first, `AudioExtractionError` second |
| `wave.open()` raises on empty WAV (0 frames) | FFmpeg failure leaves 0-byte file — test will correctly fail if extraction failed |
| lavfi codec not available in minimal FFmpeg builds | Uses `libx264` + `aac` — standard in all full FFmpeg builds; document in README |
| `conftest.py` fixture fails if FFmpeg unavailable | Entire test session skips with one clear FFmpeg error (from import-time check) |
| Windows path separators in FFmpeg command | `str(Path(...))` uses `\` on Win; FFmpeg accepts both. No issue. |

---

*Research complete — ready for planning.*
