---
plan: 03-01
phase: 03-transcription-engine
status: complete
completed: 2026-04-02
commit: 617d2ab
---

## Summary

Implemented `gensubtitles/core/transcriber.py` (replacing Phase 1 stub) and extended `gensubtitles/exceptions.py` with `TranscriptionError`.

## What Was Built

- `WhisperTranscriber(model_size, device, compute_type)` — full class with:
  - Model-size validation against `VALID_MODEL_SIZES` (raises `ValueError` with valid list)
  - `_resolve_device("auto")` — checks `torch.cuda.is_available()`, falls back to "cpu" on ImportError
  - `_default_compute_type()` — "float16" for CUDA, "int8" for CPU
  - Deferred `from faster_whisper import WhisperModel` inside `__init__` (avoids import-time penalty)
  - `BatchedInferencePipeline` wrapping when `device=="cuda"` (batch_size=16)
- `transcribe(audio_path, language=None)` — VAD always on, beam_size=5, `list(segments_gen)` to materialise generator, returns `TranscriptionResult`
- `transcribe_audio(audio_path, model_size, device, language)` — module-level convenience wrapper
- `TranscriptionResult = namedtuple("TranscriptionResult", ["segments", "language"])`
- `VALID_MODEL_SIZES` frozenset (9 entries)
- `TranscriptionError(GenSubtitlesError)` added to `exceptions.py`

## Key Files Modified

- `gensubtitles/core/transcriber.py` (replaced stub — 171 lines)
- `gensubtitles/exceptions.py` (appended TranscriptionError)

## Design Notes

- Deferred `faster_whisper` import keeps module importable without heavier dependencies at module load time
- `_resolve_device` is a `@staticmethod` to enable direct testing without instantiation
- `BatchedInferencePipeline` wrapped in try/except ImportError for graceful degradation
- `list(segments_gen)` called immediately after `model.transcribe()` — no lazy evaluation escapes (TRN-05)

## Verification

- `from gensubtitles.core.transcriber import WhisperTranscriber, VALID_MODEL_SIZES, TranscriptionResult, transcribe_audio` ✓
- `from gensubtitles.exceptions import TranscriptionError` ✓
- `WhisperTranscriber("huge")` raises `ValueError` ✓
- `len(VALID_MODEL_SIZES) == 9` ✓

## Requirements Addressed

- TRN-01: faster-whisper WhisperModel used for transcription
- TRN-02: language auto-detected when language=None (passed through to faster-whisper)
- TRN-03: model_size configurable, validated against VALID_MODEL_SIZES
- TRN-04: vad_filter=True always passed
- TRN-05: list(segments_gen) materialises generator before returning
- TRN-06: device auto-detection (cuda/cpu), compute_type selection, BatchedInferencePipeline for GPU
