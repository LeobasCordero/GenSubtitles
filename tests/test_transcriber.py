"""
Phase 3 transcription engine tests — covers TRN-01 through TRN-06.

All tests mock faster_whisper via sys.modules so they run without a GPU,
without downloading models, and without faster-whisper installed.
"""
from __future__ import annotations

from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from gensubtitles.core.transcriber import (
    VALID_DEVICES,
    VALID_MODEL_SIZES,
    TranscriptionResult,
    WhisperTranscriber,
    transcribe_audio,
)
from gensubtitles.exceptions import TranscriptionError


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_fake_segment(start: float, end: float, text: str):
    """Return a simple object with start/end/text attributes (mimics faster-whisper Segment)."""
    return SimpleNamespace(start=start, end=end, text=text)


def _make_transcription_info(language: str = "en", duration: float = 120.0):
    """Minimal TranscriptionInfo stub."""
    return SimpleNamespace(language=language, duration=duration)


def _make_model_mock(segments=None, language="en", duration: float = 120.0):
    """Build a mock WhisperModel that returns (iter(segments), info) from .transcribe()."""
    if segments is None:
        segments = [_make_fake_segment(0.0, 2.5, "Hello world")]
    info = _make_transcription_info(language, duration=duration)
    mock_model = MagicMock()
    mock_model.transcribe.return_value = (iter(segments), info)
    return mock_model


def _make_fw_module(model_mock=None, batched_cls=None):
    """Build a fake faster_whisper module for sys.modules patching."""
    fw = ModuleType("faster_whisper")
    fw.WhisperModel = MagicMock(return_value=model_mock or MagicMock())
    fw.BatchedInferencePipeline = batched_cls or MagicMock(return_value=MagicMock())
    return fw


# ── model size validation ─────────────────────────────────────────────────────


def test_valid_model_sizes_set():
    """TRN-03: VALID_MODEL_SIZES contains the documented model names."""
    assert "tiny" in VALID_MODEL_SIZES
    assert "small" in VALID_MODEL_SIZES
    assert "large-v3" in VALID_MODEL_SIZES
    assert len(VALID_MODEL_SIZES) == 9


def test_invalid_model_size_raises_value_error():
    """TRN-03: WhisperTranscriber raises ValueError for unknown model sizes."""
    with pytest.raises(ValueError, match="huge"):
        WhisperTranscriber("huge")


def test_invalid_model_size_error_lists_valid_options():
    """TRN-03: ValueError message must list valid model sizes."""
    with pytest.raises(ValueError) as exc_info:
        WhisperTranscriber("gpt-4")
    message = str(exc_info.value)
    assert "tiny" in message
    assert "small" in message


# ── device resolution ─────────────────────────────────────────────────────────


def test_resolve_device_explicit_cpu():
    """TRN-06: Explicit device='cpu' passes through unchanged."""
    assert WhisperTranscriber._resolve_device("cpu") == "cpu"


def test_resolve_device_explicit_cuda():
    """TRN-06: Explicit device='cuda' passes through unchanged."""
    assert WhisperTranscriber._resolve_device("cuda") == "cuda"


def test_resolve_device_auto_no_cuda():
    """TRN-06: device='auto' resolves to 'cpu' when torch is absent (ImportError)."""
    original_import = __import__

    def _import_without_torch(name, *args, **kwargs):
        if name == "torch":
            raise ImportError("No module named 'torch'")
        return original_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=_import_without_torch):
        result = WhisperTranscriber._resolve_device("auto")
    assert result == "cpu"


def test_resolve_device_auto_no_cuda_attribute_error():
    """TRN-06: device='auto' resolves to 'cpu' when torch lacks cuda (AttributeError)."""
    mock_torch = MagicMock(spec=[])  # no .cuda attribute
    with patch.dict("sys.modules", {"torch": mock_torch}):
        result = WhisperTranscriber._resolve_device("auto")
    assert result == "cpu"


def test_resolve_device_auto_with_cuda():
    """TRN-06: device='auto' resolves to 'cuda' when torch.cuda.is_available() is True."""
    mock_torch = MagicMock()
    mock_torch.cuda.is_available.return_value = True
    with patch.dict("sys.modules", {"torch": mock_torch}):
        result = WhisperTranscriber._resolve_device("auto")
    assert result == "cuda"


# ── WhisperTranscriber init ───────────────────────────────────────────────────


def test_whisper_transcriber_init_cpu():
    """TRN-01, TRN-06: WhisperTranscriber('tiny', device='cpu') initializes without error."""
    fw = _make_fw_module()
    with patch.dict("sys.modules", {"faster_whisper": fw}):
        transcriber = WhisperTranscriber("tiny", device="cpu")
    assert transcriber.model is not None


def test_whisper_transcriber_compute_type_int8_for_cpu():
    """TRN-06: CPU device defaults to int8 compute_type."""
    fw = _make_fw_module()
    with patch.dict("sys.modules", {"faster_whisper": fw}):
        WhisperTranscriber("tiny", device="cpu")
    _args, kwargs = fw.WhisperModel.call_args
    assert kwargs.get("compute_type") == "int8"


def test_whisper_transcriber_compute_type_float16_for_cuda():
    """TRN-06: CUDA device defaults to float16 compute_type."""
    fw = _make_fw_module()
    mock_torch = MagicMock()
    mock_torch.cuda.is_available.return_value = True
    with patch.dict("sys.modules", {"faster_whisper": fw, "torch": mock_torch}):
        WhisperTranscriber("tiny", device="auto")
    _args, kwargs = fw.WhisperModel.call_args
    assert kwargs.get("compute_type") == "float16"


# ── transcribe() ──────────────────────────────────────────────────────────────


def test_transcribe_returns_transcription_result():
    """TRN-01: transcribe() returns a TranscriptionResult named tuple."""
    segments = [_make_fake_segment(0.0, 1.0, "Hello"), _make_fake_segment(1.0, 2.0, "World")]
    mock_model = _make_model_mock(segments=segments, language="en")
    fw = _make_fw_module(model_mock=mock_model)
    with patch.dict("sys.modules", {"faster_whisper": fw}):
        transcriber = WhisperTranscriber("tiny", device="cpu")
    transcriber.model = mock_model
    result = transcriber.transcribe("fake_audio.wav")
    assert isinstance(result, TranscriptionResult)
    assert isinstance(result.segments, list)
    assert result.language == "en"


def test_transcribe_duration_is_populated():
    """TranscriptionResult.duration is a float threaded through from info.duration."""
    mock_model = _make_model_mock(duration=42.5)
    fw = _make_fw_module(model_mock=mock_model)
    with patch.dict("sys.modules", {"faster_whisper": fw}):
        transcriber = WhisperTranscriber("tiny", device="cpu")
    transcriber.model = mock_model
    result = transcriber.transcribe("fake.wav")
    assert isinstance(result.duration, float)
    assert result.duration == 42.5


def test_transcribe_segments_are_list():
    """TRN-05: segments generator is materialised as a list before returning."""
    segments = [_make_fake_segment(0.0, 2.5, "Test segment")]
    mock_model = _make_model_mock(segments=segments)
    fw = _make_fw_module(model_mock=mock_model)
    with patch.dict("sys.modules", {"faster_whisper": fw}):
        transcriber = WhisperTranscriber("tiny", device="cpu")
    transcriber.model = mock_model
    result = transcriber.transcribe("fake_audio.wav")
    assert type(result.segments) is list, "segments must be a list, not a generator"
    assert len(result.segments) == 1


def test_transcribe_vad_filter_always_true():
    """TRN-04: vad_filter=True is always passed to model.transcribe()."""
    mock_model = _make_model_mock()
    fw = _make_fw_module(model_mock=mock_model)
    with patch.dict("sys.modules", {"faster_whisper": fw}):
        transcriber = WhisperTranscriber("tiny", device="cpu")
    transcriber.model = mock_model
    transcriber.transcribe("fake.wav")
    _args, kwargs = mock_model.transcribe.call_args
    assert kwargs.get("vad_filter") is True


def test_transcribe_language_auto_detect():
    """TRN-02: When language=None, result.language is auto-detected (returned by model)."""
    mock_model = _make_model_mock(language="fr")
    fw = _make_fw_module(model_mock=mock_model)
    with patch.dict("sys.modules", {"faster_whisper": fw}):
        transcriber = WhisperTranscriber("tiny", device="cpu")
    transcriber.model = mock_model
    result = transcriber.transcribe("fake.wav")  # no language arg
    assert result.language == "fr"


def test_transcribe_explicit_language_passed():
    """TRN-02: When language is provided, it is forwarded to model.transcribe()."""
    mock_model = _make_model_mock(language="de")
    fw = _make_fw_module(model_mock=mock_model)
    with patch.dict("sys.modules", {"faster_whisper": fw}):
        transcriber = WhisperTranscriber("tiny", device="cpu")
    transcriber.model = mock_model
    transcriber.transcribe("fake.wav", language="de")
    _args, kwargs = mock_model.transcribe.call_args
    assert kwargs.get("language") == "de"


def test_transcribe_segment_attributes():
    """TRN-01: Each segment has start, end (floats) and text (non-empty str)."""
    segments = [_make_fake_segment(1.5, 3.0, "  spoken text  ")]
    mock_model = _make_model_mock(segments=segments)
    fw = _make_fw_module(model_mock=mock_model)
    with patch.dict("sys.modules", {"faster_whisper": fw}):
        transcriber = WhisperTranscriber("tiny", device="cpu")
    transcriber.model = mock_model
    result = transcriber.transcribe("fake.wav")
    seg = result.segments[0]
    assert isinstance(seg.start, float)
    assert isinstance(seg.end, float)
    assert isinstance(seg.text, str)
    assert len(seg.text.strip()) > 0


# ── transcribe_audio convenience ─────────────────────────────────────────────


def test_transcribe_audio_convenience():
    """TRN-01: transcribe_audio() returns TranscriptionResult without manually building transcriber."""
    segments = [_make_fake_segment(0.0, 1.0, "Convenience test")]
    mock_model = _make_model_mock(segments=segments, language="en")
    fw = _make_fw_module(model_mock=mock_model)
    with patch.dict("sys.modules", {"faster_whisper": fw}):
        result = transcribe_audio("fake.wav", model_size="tiny", device="cpu")
    assert isinstance(result, TranscriptionResult)
    assert result.language == "en"
    assert len(result.segments) == 1


def test_transcribe_audio_duration_is_populated():
    """transcribe_audio() result.duration is threaded through from info.duration."""
    mock_model = _make_model_mock(duration=75.0)
    fw = _make_fw_module(model_mock=mock_model)
    with patch.dict("sys.modules", {"faster_whisper": fw}):
        result = transcribe_audio("fake.wav", model_size="tiny", device="cpu")
    assert isinstance(result.duration, float)
    assert result.duration == 75.0


def test_transcription_error_is_gen_subtitles_error():
    """TranscriptionError is a subclass of GenSubtitlesError."""
    from gensubtitles.exceptions import GenSubtitlesError
    assert issubclass(TranscriptionError, GenSubtitlesError)


# ── device validation ─────────────────────────────────────────────────────────


def test_invalid_device_raises_value_error():
    """device must be one of VALID_DEVICES; others raise ValueError."""
    with pytest.raises(ValueError, match="cdua"):
        WhisperTranscriber("tiny", device="cdua")


def test_invalid_device_error_lists_valid_options():
    """ValueError for invalid device must list valid options."""
    with pytest.raises(ValueError) as exc_info:
        WhisperTranscriber("tiny", device="gpu")
    message = str(exc_info.value)
    for valid in VALID_DEVICES:
        assert valid in message


def test_valid_devices_set():
    """VALID_DEVICES contains exactly auto, cpu, cuda."""
    assert VALID_DEVICES == frozenset({"auto", "cpu", "cuda"})


# ── TranscriptionError surface ────────────────────────────────────────────────


def test_transcription_error_on_model_init_failure():
    """TranscriptionError is raised (not library exception) when WhisperModel init fails."""
    fw = _make_fw_module()
    fw.WhisperModel.side_effect = RuntimeError("model load failed")
    with patch.dict("sys.modules", {"faster_whisper": fw}):
        with pytest.raises(TranscriptionError, match="model load failed"):
            WhisperTranscriber("tiny", device="cpu")


def test_transcription_error_on_transcribe_failure():
    """TranscriptionError is raised when model.transcribe() fails."""
    mock_model = _make_model_mock()
    mock_model.transcribe.side_effect = RuntimeError("transcription boom")
    fw = _make_fw_module(model_mock=mock_model)
    with patch.dict("sys.modules", {"faster_whisper": fw}):
        transcriber = WhisperTranscriber("tiny", device="cpu")
    transcriber.model = mock_model
    with pytest.raises(TranscriptionError, match="transcription boom"):
        transcriber.transcribe("fake.wav")


def test_transcription_error_chains_original_exception():
    """TranscriptionError.__cause__ is the original exception from faster-whisper."""
    original_exc = RuntimeError("underlying error")
    mock_model = _make_model_mock()
    mock_model.transcribe.side_effect = original_exc
    fw = _make_fw_module(model_mock=mock_model)
    with patch.dict("sys.modules", {"faster_whisper": fw}):
        transcriber = WhisperTranscriber("tiny", device="cpu")
    transcriber.model = mock_model
    with pytest.raises(TranscriptionError) as exc_info:
        transcriber.transcribe("fake.wav")
    assert exc_info.value.__cause__ is original_exc
