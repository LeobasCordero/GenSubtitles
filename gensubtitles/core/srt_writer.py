"""
gensubtitles.core.srt_writer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Subtitle file generation using the `srt` and `pysubs2` libraries.

Provides:
    OutputFormat
        Enum of supported output formats (SRT, SSA).

    segments_to_srt(segments) -> str
        Convert duck-typed segment objects to SRT-formatted string.

    write_srt(segments, output_path: str | Path) -> None
        Write SRT content to a file (creates parent dirs if needed).

    write_ssa(segments, output_path: str | Path) -> None
        Write SSA-formatted subtitles using pysubs2.

    convert_srt_to_ssa(srt_path, ssa_path) -> None
        Convert an existing .srt file to .ssa using pysubs2.

    convert_ssa_to_srt(ssa_path, srt_path) -> None
        Convert an existing .ssa file to .srt using pysubs2.
"""
from __future__ import annotations

import logging
from collections.abc import Iterable
from datetime import timedelta
from enum import Enum
from pathlib import Path
from typing import Any

import srt

logger = logging.getLogger(__name__)


class OutputFormat(str, Enum):
    SRT = "srt"
    SSA = "ssa"


def segments_to_srt(segments: Iterable[Any]) -> str:
    """
    Convert an iterable of duck-typed segment objects to an SRT-formatted string.

    Each segment must have:
        .start (float): start time in seconds
        .end   (float): end time in seconds
        .text  (str):   subtitle text (stripped before writing)

    Returns an empty string for an empty iterable of segments.
    """
    segments = list(segments)
    if not segments:
        return ""

    subtitles = [
        srt.Subtitle(
            index=i + 1,
            start=timedelta(seconds=seg.start),
            end=timedelta(seconds=seg.end),
            content=seg.text.strip(),
        )
        for i, seg in enumerate(segments)
    ]
    return srt.compose(subtitles)


def write_srt(segments: Iterable[Any], output_path: str | Path) -> None:
    """
    Write SRT-formatted subtitles to a file.

    Args:
        segments:    Iterable of duck-typed segment objects (.start, .end, .text).
        output_path: Destination file path (str or Path). Parent dirs are created
                     automatically if they do not exist.

    If segments is empty, an empty file is written and a warning is logged.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    srt_content = segments_to_srt(segments)

    if not srt_content:
        logger.warning(
            "write_srt: segment list is empty — writing empty SRT file to %s",
            output_path,
        )

    output_path.write_text(srt_content, encoding="utf-8")


def write_ssa(segments: Iterable[Any], output_path: str | Path) -> None:
    """
    Write SSA-formatted subtitles to a file using pysubs2.

    Args:
        segments:    Iterable of duck-typed segment objects (.start, .end, .text).
        output_path: Destination file path (str or Path). Parent dirs are created
                     automatically if they do not exist.
    """
    import pysubs2

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    subs = pysubs2.SSAFile()
    for seg in segments:
        event = pysubs2.SSAEvent(
            start=pysubs2.make_time(s=seg.start),
            end=pysubs2.make_time(s=seg.end),
            text=seg.text.strip(),
        )
        subs.append(event)

    subs.save(str(output_path))


def convert_srt_to_ssa(srt_path: str | Path, ssa_path: str | Path) -> None:
    """
    Convert an existing .srt file to .ssa using pysubs2.

    Args:
        srt_path: Source SRT file path.
        ssa_path: Destination SSA file path.
    """
    import pysubs2

    subs = pysubs2.SSAFile.load(str(srt_path))
    subs.save(str(ssa_path))


def convert_ssa_to_srt(ssa_path: str | Path, srt_path: str | Path) -> None:
    """
    Convert an existing .ssa file to .srt using pysubs2.

    Args:
        ssa_path: Source SSA file path.
        srt_path: Destination SRT file path.
    """
    import pysubs2

    subs = pysubs2.SSAFile.load(str(ssa_path))
    subs.save(str(srt_path), format_="srt")
