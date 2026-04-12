"""
gensubtitles.core.pipeline
~~~~~~~~~~~~~~~~~~~~~~~~~~
Central orchestration layer — wires audio extraction → transcription →
translation (optional) → SRT write into a single callable used by both
the CLI (Phase 7) and FastAPI layer (Phase 8).

Provides:
    PipelineResult  — dataclass returned by run_pipeline()
    run_pipeline()  — main entry point for subtitle generation
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from gensubtitles.exceptions import PipelineError

logger = logging.getLogger(__name__)


# ── result type ───────────────────────────────────────────────────────────────

@dataclass
class PipelineResult:
    srt_path: str
    detected_language: str
    segment_count: int
    audio_duration_seconds: float


# ── public API ────────────────────────────────────────────────────────────────

def run_pipeline(
    video_path: str | Path,
    output_path: str | Path,
    model_size: str = "medium",
    target_lang: Optional[str] = None,
    source_lang: Optional[str] = None,
    device: str = "auto",
    progress_callback: Optional[Callable[[str, int, int], None]] = None,
) -> PipelineResult:
    """
    Orchestrate audio extraction → transcription → translation → SRT write.

    Args:
        video_path:        Path to the input video file.
        output_path:       Destination path for the generated .srt file.
        model_size:        faster-whisper model size (default "medium").
        target_lang:       ISO 639-1 target language for translation;
                           None skips translation entirely.
        source_lang:       Force audio source language; None = auto-detect.
        device:            Compute device: "auto", "cpu", or "cuda".
        progress_callback: Optional callable receiving (label, current, total).
                           Called once per stage with total=4.

    Returns:
        PipelineResult with srt_path, detected_language, segment_count,
        and audio_duration_seconds.

    Raises:
        FileNotFoundError: If video_path does not exist on disk.
        PipelineError:     If any pipeline stage raises an exception.
    """
    video_path = Path(video_path)
    output_path = Path(output_path)

    # ── input validation (before any subprocess or optional dependency checks) ──
    if not video_path.is_file():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    # Ensure output parent dir exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Lazy imports — several sub-modules have import-time side effects or heavy
    # optional dependencies (FFmpeg check in audio.py, srt/argostranslate/faster-whisper).
    # Deferring them until after path validation ensures missing-input errors are
    # raised without requiring optional runtime dependencies to be available.
    from gensubtitles.core.audio import audio_temp_context, extract_audio  # noqa: PLC0415
    from gensubtitles.core.srt_writer import write_srt  # noqa: PLC0415
    from gensubtitles.core.transcriber import WhisperTranscriber  # noqa: PLC0415
    from gensubtitles.core.translator import translate_segments  # noqa: PLC0415

    # Default no-op callback
    if progress_callback is None:
        progress_callback = lambda *_: None  # noqa: E731

    with audio_temp_context() as wav_path:

        # ── Stage 1: Extract audio ────────────────────────────────────────────
        progress_callback("Extracting audio", 1, 4)
        try:
            extract_audio(video_path, wav_path)
        except Exception as exc:
            raise PipelineError(f"[audio_extraction] {exc}") from exc

        # ── Stage 2: Transcribe ───────────────────────────────────────────────
        progress_callback("Transcribing", 2, 4)
        try:
            transcriber = WhisperTranscriber(model_size=model_size, device=device)
            transcription = transcriber.transcribe(wav_path, language=source_lang)
        except Exception as exc:
            raise PipelineError(f"[transcription] {exc}") from exc

        detected_lang = transcription.language
        segments = transcription.segments

        # ── Stage 3: Translate (conditional) ─────────────────────────────────
        if target_lang is not None:
            progress_callback("Translating", 3, 4)
            try:
                segments = translate_segments(segments, detected_lang, target_lang)
            except Exception as exc:
                raise PipelineError(f"[translation] {exc}") from exc
        else:
            progress_callback("Translation skipped", 3, 4)

        # ── Stage 4: Write SRT ────────────────────────────────────────────────
        progress_callback("Writing SRT", 4, 4)
        try:
            write_srt(segments, output_path)
        except Exception as exc:
            raise PipelineError(f"[srt_writing] {exc}") from exc

    logger.info(
        "Pipeline complete: %d segments, lang=%r, duration=%.1fs → %s",
        len(segments),
        detected_lang,
        transcription.duration,
        output_path,
    )

    return PipelineResult(
        srt_path=str(output_path),
        detected_language=detected_lang,
        segment_count=len(segments),
        audio_duration_seconds=transcription.duration,
    )
