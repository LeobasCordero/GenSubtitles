"""
gensubtitles.core.srt_writer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
SRT file generation using the `srt` library.

Provides:
    segments_to_srt(segments) -> str
        Convert duck-typed segment objects to SRT-formatted string.

    write_srt(segments, output_path: str | Path) -> None
        Write SRT content to a file (creates parent dirs if needed).
"""
from __future__ import annotations

import logging
from datetime import timedelta
from pathlib import Path

import srt

logger = logging.getLogger(__name__)


def segments_to_srt(segments) -> str:
    """
    Convert a list of duck-typed segment objects to an SRT-formatted string.

    Each segment must have:
        .start (float): start time in seconds
        .end   (float): end time in seconds
        .text  (str):   subtitle text (stripped before writing)

    Returns an empty string for an empty segment list.
    """
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


def write_srt(segments, output_path: str | Path) -> None:
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
