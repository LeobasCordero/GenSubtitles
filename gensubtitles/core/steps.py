"""
gensubtitles.core.steps
~~~~~~~~~~~~~~~~~~~~~~~
Individual pipeline step functions for stepper mode.

Each function reads/writes a specific intermediate artefact from/to a
user-supplied work directory so subsequent steps can resume without
repeating completed work.

Artefact filenames (constants exported for use by CLI, API, GUI):
    AUDIO_FILENAME         = "audio.wav"
    TRANSCRIPTION_FILENAME = "transcription.json"
    TRANSLATION_FILENAME   = "translation.json"
    SRT_FILENAME           = "subtitles.srt"

Step functions:
    extract_audio_step()   — video → audio.wav
    transcribe_step()      — audio.wav → transcription.json
    translate_step()       — transcription.json → translation.json
    write_srt_step()       — translation.json (or transcription.json) → .srt

JSON helpers:
    segments_to_json()     — serialize segments to [{start, end, text}]
    segments_from_json()   — deserialize back (duck-typed, works with write_srt)
"""
from __future__ import annotations

import json
import logging
from collections import namedtuple
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    from gensubtitles.core.transcriber import TranscriptionResult, WhisperTranscriber

logger = logging.getLogger(__name__)

# ── artefact filename constants ───────────────────────────────────────────────

AUDIO_FILENAME: str = "audio.wav"
TRANSCRIPTION_FILENAME: str = "transcription.json"
TRANSLATION_FILENAME: str = "translation.json"
SRT_FILENAME: str = "subtitles.srt"

# ── internal deserialization namedtuple ───────────────────────────────────────
# Duck-typed: write_srt() and translate_segments() only need .start, .end, .text
_Segment = namedtuple("_Segment", ["start", "end", "text"])


# ── JSON helpers ──────────────────────────────────────────────────────────────

def segments_to_json(
    segments,
    path: str | Path,
    metadata: Optional[dict] = None,
) -> None:
    """Serialize an iterable of segment-like objects to a JSON file.

    When *metadata* is provided (e.g. ``{"language": "en", "duration": 12.5}``),
    the file is written as::

        {"language": ..., "duration": ..., "segments": [{start, end, text}, ...]}

    Without *metadata*, the file is a plain array::

        [{start, end, text}, ...]

    Args:
        segments: Iterable with duck-typed .start, .end, .text attributes.
        path:     Output file path. Parent directory must exist.
        metadata: Optional dict of extra top-level fields (language, duration).
    """
    segs = [{"start": s.start, "end": s.end, "text": s.text} for s in segments]
    path = Path(path)
    if metadata is not None:
        data: object = {**metadata, "segments": segs}
    else:
        data = segs
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.debug("Wrote %d segments to %s", len(segs), path)


def segments_from_json(path: str | Path) -> list[_Segment]:
    """Deserialize a segments JSON file back to a list of _Segment namedtuples.

    Handles both formats:
    - Dict format: ``{"language": ..., "segments": [...]}``  (transcription.json)
    - List format: ``[{start, end, text}, ...]``             (translation.json)

    Returns objects with .start (float), .end (float), .text (str) usable by
    write_srt() and translate_segments().
    """
    path = Path(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        items = raw.get("segments", [])
    else:
        items = raw
    return [_Segment(start=item["start"], end=item["end"], text=item["text"]) for item in items]


# ── step functions ────────────────────────────────────────────────────────────

def extract_audio_step(
    video_path: str | Path,
    work_dir: str | Path,
    progress_callback: Optional[Callable[[str, int, int], None]] = None,
) -> Path:
    """Stage 1: Extract audio from video, write audio.wav to work_dir.

    Args:
        video_path: Path to input video file.
        work_dir:   Directory where audio.wav will be written.
        progress_callback: Optional callable(label, current, total).

    Returns:
        Path to the written audio.wav file.

    Raises:
        FileNotFoundError: If video_path does not exist.
        AudioExtractionError: If FFmpeg fails.
    """
    from gensubtitles.core.audio import extract_audio  # noqa: PLC0415

    video_path = Path(video_path)
    work_dir = Path(work_dir)

    if not video_path.is_file():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    work_dir.mkdir(parents=True, exist_ok=True)
    wav_path = work_dir / AUDIO_FILENAME

    if progress_callback is not None:
        progress_callback("Extracting audio", 1, 4)

    extract_audio(video_path, wav_path)
    logger.info("extract_audio_step: wrote %s", wav_path)
    return wav_path


def transcribe_step(
    work_dir: str | Path,
    transcriber: Optional["WhisperTranscriber"] = None,
    model_size: str = "medium",
    source_lang: Optional[str] = None,
    device: str = "auto",
    progress_callback: Optional[Callable[[str, int, int], None]] = None,
) -> "TranscriptionResult":
    """Stage 2: Transcribe audio.wav, write transcription.json to work_dir.

    The transcription JSON is written in dict format::

        {"language": "en", "duration": 12.5, "segments": [{start, end, text}, ...]}

    Args:
        work_dir:     Directory containing audio.wav; transcription.json written here.
        transcriber:  Pre-loaded WhisperTranscriber (pass from API lifespan to avoid
                      re-loading model). If None, a new instance is created.
        model_size:   Whisper model size (used only when transcriber=None).
        source_lang:  Force source language (None = auto-detect).
        device:       Compute device (used only when transcriber=None).
        progress_callback: Optional callable(label, current, total).

    Returns:
        TranscriptionResult(segments, language, duration).

    Raises:
        FileNotFoundError: If audio.wav is not present in work_dir.
    """
    from gensubtitles.core.transcriber import WhisperTranscriber  # noqa: PLC0415

    work_dir = Path(work_dir)
    wav_path = work_dir / AUDIO_FILENAME

    if not wav_path.is_file():
        raise FileNotFoundError(f"audio.wav not found in work_dir: {wav_path}")

    if transcriber is None:
        transcriber = WhisperTranscriber(model_size=model_size, device=device)

    if progress_callback is not None:
        progress_callback("Transcribing", 2, 4)

    result = transcriber.transcribe(wav_path, language=source_lang)
    segments_to_json(
        result.segments,
        work_dir / TRANSCRIPTION_FILENAME,
        metadata={"language": result.language, "duration": result.duration},
    )
    logger.info(
        "transcribe_step: %d segments, lang=%r → %s",
        len(result.segments),
        result.language,
        work_dir / TRANSCRIPTION_FILENAME,
    )
    return result


def translate_step(
    work_dir: str | Path,
    target_lang: str,
    engine: str = "argos",
    progress_callback: Optional[Callable[[str, int, int], None]] = None,
) -> list:
    """Stage 3: Translate transcription.json, write translation.json to work_dir.

    Args:
        work_dir:    Directory containing transcription.json; translation.json written here.
        target_lang: ISO 639-1 target language code (e.g. 'es', 'fr').
        engine:      Translation engine ('argos', 'deepl', 'libretranslate').
        progress_callback: Optional callable(label, current, total).

    Returns:
        List of translated segments (namedtuple with .start, .end, .text).

    Raises:
        FileNotFoundError: If transcription.json is not present in work_dir.
    """
    from gensubtitles.core.translator import translate_segments  # noqa: PLC0415

    work_dir = Path(work_dir)
    trans_path = work_dir / TRANSCRIPTION_FILENAME

    if not trans_path.is_file():
        raise FileNotFoundError(f"transcription.json not found in work_dir: {trans_path}")

    if progress_callback is not None:
        progress_callback("Translating", 3, 4)

    segments = segments_from_json(trans_path)
    source_lang = _read_source_lang(work_dir)
    translated = translate_segments(segments, source_lang, target_lang, engine=engine)
    translated = list(translated)
    segments_to_json(translated, work_dir / TRANSLATION_FILENAME)
    logger.info(
        "translate_step: %d segments → %s",
        len(translated),
        work_dir / TRANSLATION_FILENAME,
    )
    return translated


def write_srt_step(
    work_dir: str | Path,
    output_path: str | Path,
    progress_callback: Optional[Callable[[str, int, int], None]] = None,
) -> Path:
    """Stage 4: Write SRT from translation.json (if present) or transcription.json.

    Args:
        work_dir:    Directory containing JSON artefacts from prior steps.
        output_path: Destination path for the .srt file.
        progress_callback: Optional callable(label, current, total).

    Returns:
        Path to the written SRT file.

    Raises:
        FileNotFoundError: If neither translation.json nor transcription.json
                           exists in work_dir.
    """
    from gensubtitles.core.srt_writer import write_srt  # noqa: PLC0415

    work_dir = Path(work_dir)
    output_path = Path(output_path)

    translation_path = work_dir / TRANSLATION_FILENAME
    transcription_path = work_dir / TRANSCRIPTION_FILENAME

    if translation_path.is_file():
        segments = segments_from_json(translation_path)
        source = "translation.json"
    elif transcription_path.is_file():
        segments = segments_from_json(transcription_path)
        source = "transcription.json"
    else:
        raise FileNotFoundError(
            f"No segments JSON found in work_dir {work_dir}. "
            f"Run transcribe or translate step first."
        )

    if progress_callback is not None:
        progress_callback("Writing SRT", 4, 4)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_srt(segments, output_path)
    logger.info("write_srt_step: %s → %s", source, output_path)
    return output_path


# ── internal helpers ──────────────────────────────────────────────────────────

def _read_source_lang(work_dir: Path) -> str:
    """Read the detected source language stored in transcription.json metadata.

    Raises ``ValueError`` if the language field is absent so that callers get a
    clear error rather than silently passing an unsupported "auto" value to
    ``translate_segments()`` (which requires a real ISO 639-1 code).

    Note: callers must ensure transcription.json exists before calling this helper.
    """
    trans_path = work_dir / TRANSCRIPTION_FILENAME
    raw = json.loads(trans_path.read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        lang = raw.get("language")
        if lang:
            return lang
        raise ValueError(
            f"{TRANSCRIPTION_FILENAME} does not contain a 'language' field. "
            "Re-run transcribe_step to regenerate the file with language detection."
        )
    raise ValueError(
        f"{TRANSCRIPTION_FILENAME} uses a legacy flat-list format that does not "
        "store the source language. Re-run transcribe_step to regenerate the file."
    )
