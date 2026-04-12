"""
gensubtitles.core.transcriber
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
faster-whisper based transcription engine.

Provides:
    WhisperTranscriber — configurable transcription class (reuse model across calls)
    transcribe_audio()  — module-level convenience function (single-call use)
    TranscriptionResult — named tuple returned by both paths
    VALID_MODEL_SIZES   — frozenset of supported model size strings
"""
from __future__ import annotations

import logging
from collections import namedtuple
from pathlib import Path
from typing import Optional

from gensubtitles.exceptions import TranscriptionError

logger = logging.getLogger(__name__)

# ── valid model sizes ─────────────────────────────────────────────────────────
VALID_MODEL_SIZES: frozenset[str] = frozenset(
    {
        "tiny",
        "base",
        "small",
        "medium",
        "large-v1",
        "large-v2",
        "large-v3",
        "turbo",
        "distil-large-v3",
    }
)

VALID_DEVICES: frozenset[str] = frozenset({"auto", "cpu", "cuda"})

# ── result type ───────────────────────────────────────────────────────────────
TranscriptionResult = namedtuple("TranscriptionResult", ["segments", "language", "duration"])


class WhisperTranscriber:
    """
    Wraps a faster-whisper WhisperModel with auto device/compute_type selection,
    model-size validation, and VAD-filtered transcription.

    Usage:
        transcriber = WhisperTranscriber(model_size="medium", device="auto")
        result = transcriber.transcribe("audio.wav")
        for seg in result.segments:
            print(seg.start, seg.end, seg.text)
    """

    def __init__(
        self,
        model_size: str = "medium",
        device: str = "auto",
        compute_type: Optional[str] = None,
    ) -> None:
        if model_size not in VALID_MODEL_SIZES:
            sorted_sizes = sorted(VALID_MODEL_SIZES)
            raise ValueError(
                f"Invalid model_size {model_size!r}. "
                f"Valid options: {sorted_sizes}"
            )

        if device not in VALID_DEVICES:
            sorted_devices = sorted(VALID_DEVICES)
            raise ValueError(
                f"Invalid device {device!r}. "
                f"Valid options: {sorted_devices}"
            )

        resolved_device = self._resolve_device(device)
        resolved_compute = compute_type or self._default_compute_type(resolved_device)

        logger.info(
            "Loading WhisperModel %r on device=%r compute_type=%r",
            model_size,
            resolved_device,
            resolved_compute,
        )

        try:
            from faster_whisper import WhisperModel  # deferred — heavy import

            self._model_raw = WhisperModel(
                model_size,
                device=resolved_device,
                compute_type=resolved_compute,
            )
        except Exception as exc:
            raise TranscriptionError(
                f"Failed to load WhisperModel {model_size!r} on {resolved_device!r}: {exc}"
            ) from exc

        self._device = resolved_device

        # Wrap in BatchedInferencePipeline for GPU throughput
        if resolved_device == "cuda":
            try:
                from faster_whisper import BatchedInferencePipeline

                self.model = BatchedInferencePipeline(model=self._model_raw)
                logger.info("BatchedInferencePipeline enabled (batch_size=16)")
            except ImportError:
                logger.warning(
                    "BatchedInferencePipeline not available — using standard model"
                )
                self.model = self._model_raw
        else:
            self.model = self._model_raw

    # ── public API ────────────────────────────────────────────────────────────

    def transcribe(
        self,
        audio_path: str | Path,
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """
        Transcribe *audio_path* and return a TranscriptionResult.

        VAD filter is always enabled to suppress hallucinations on silence (TRN-04).
        The segments generator is fully consumed before returning (TRN-05).

        Args:
            audio_path: Path to a WAV (or any audio) file.
            language:   ISO 639-1 code, e.g. "en". None = auto-detect (TRN-02).

        Returns:
            TranscriptionResult(segments=list[Segment], language=str, duration=float)
            where duration is the total audio duration in seconds.
        """
        kwargs: dict = {"vad_filter": True, "beam_size": 5}
        # TRN-VAD: tuned silence detection (D-01)
        kwargs["vad_parameters"] = {
            "min_silence_duration_ms": 400,
            "speech_pad_ms": 200,
            "min_speech_duration_ms": 250,
        }
        # TRN-WT: word-level timestamps for end-time tightening (D-02)
        kwargs["word_timestamps"] = True
        if language is not None:
            kwargs["language"] = language
        if self._device == "cuda":
            kwargs["batch_size"] = 16

        try:
            segments_gen, info = self.model.transcribe(str(audio_path), **kwargs)

            # TRN-05: materialise the lazy generator immediately to ensure transcription
            # completes before caller receives control.
            segments = list(segments_gen)

            # TRN-WT: tighten end-times and drop wordless segments (D-03, D-04)
            patched: list = []
            for seg in segments:
                words = getattr(seg, "words", None)
                if not words:  # None or empty list — silence-only segment, drop (D-04)
                    continue
                try:
                    seg = seg._replace(end=words[-1].end)  # namedtuple path (D-03)
                except AttributeError:
                    import copy as _copy
                    seg = _copy.copy(seg)
                    seg.end = words[-1].end  # SimpleNamespace fallback (D-03)
                patched.append(seg)
            segments = patched
        except Exception as exc:
            raise TranscriptionError(
                f"Transcription failed for {audio_path!r}: {exc}"
            ) from exc

        logger.info(
            "Transcription complete: %d segments, language=%r",
            len(segments),
            info.language,
        )
        return TranscriptionResult(segments=segments, language=info.language, duration=info.duration)

    # ── private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _resolve_device(device: str) -> str:
        """Resolve 'auto' to 'cuda' or 'cpu' based on torch availability."""
        if device != "auto":
            return device
        try:
            import torch  # noqa: PLC0415

            if torch.cuda.is_available():
                logger.info("CUDA available — resolving device to 'cuda'")
                return "cuda"
        except (ImportError, AttributeError):
            pass
        logger.info("CUDA not available — resolving device to 'cpu'")
        return "cpu"

    @staticmethod
    def _default_compute_type(device: str) -> str:
        """Return sensible compute_type for the resolved device."""
        return "float16" if device == "cuda" else "int8"


# ── module-level convenience function ─────────────────────────────────────────


def transcribe_audio(
    audio_path: str | Path,
    model_size: str = "medium",
    device: str = "auto",
    language: Optional[str] = None,
) -> TranscriptionResult:
    """
    One-shot convenience wrapper — creates a WhisperTranscriber and calls
    transcribe().  Use WhisperTranscriber directly when reusing the model
    across multiple audio files.

    Args:
        audio_path:  Path to audio file.
        model_size:  One of VALID_MODEL_SIZES (default "medium").
        device:      "auto", "cpu", or "cuda".
        language:    ISO 639-1 code or None for auto-detect.

    Returns:
        TranscriptionResult(segments, language, duration) where duration is
        the total audio duration in seconds.
    """
    transcriber = WhisperTranscriber(model_size=model_size, device=device)
    return transcriber.transcribe(audio_path, language=language)
