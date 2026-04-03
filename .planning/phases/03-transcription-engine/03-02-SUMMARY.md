---
plan: 03-02
phase: 03-transcription-engine
status: complete
completed: 2026-04-02
commit: 64612c4
---

## Summary

Created `tests/test_transcriber.py` with 18 unit tests covering all TRN requirements. Tests mock `faster_whisper` via `sys.modules` — no GPU, no model download, no faster-whisper install required.

## What Was Built

18 tests across 7 categories:
1. **Model size validation** (3 tests) — VALID_MODEL_SIZES contents, ValueError on invalid size, error message lists valid options
2. **Device resolution** (4 tests) — explicit cpu/cuda pass-through, auto→cpu when torch absent, auto→cuda when `torch.cuda.is_available()=True`
3. **Initializer** (3 tests) — successful init with CPU, int8 compute_type for CPU, float16 compute_type for CUDA
4. **transcribe() method** (6 tests) — returns TranscriptionResult, segments are list (not generator), vad_filter=True always, language auto-detect, explicit language forwarded, segment attributes (start/end/text)
5. **transcribe_audio() convenience** (1 test) — end-to-end convenience function
6. **Exception hierarchy** (1 test) — TranscriptionError is subclass of GenSubtitlesError

## Key Design Decision

Used `patch.dict("sys.modules", {"faster_whisper": fake_module})` instead of `patch("faster_whisper.WhisperModel")`. The deferred import in `WhisperTranscriber.__init__` means the module must be present in `sys.modules` at import time of that statement — `_make_fw_module()` helper creates a complete fake module with `WhisperModel` and `BatchedInferencePipeline` attributes.

## Verification

- `pytest tests/test_transcriber.py -v` → 18 passed in 0.40s ✓
- All 6 TRN requirements covered

## Requirements Addressed

- TRN-01: test_transcribe_returns_transcription_result, test_transcribe_segment_attributes
- TRN-02: test_transcribe_language_auto_detect, test_transcribe_explicit_language_passed
- TRN-03: test_valid_model_sizes_set, test_invalid_model_size_raises_value_error, test_invalid_model_size_error_lists_valid_options
- TRN-04: test_transcribe_vad_filter_always_true
- TRN-05: test_transcribe_segments_are_list
- TRN-06: test_resolve_device_auto_no_cuda, test_resolve_device_auto_with_cuda, test_whisper_transcriber_compute_type_int8_for_cpu, test_whisper_transcriber_compute_type_float16_for_cuda
