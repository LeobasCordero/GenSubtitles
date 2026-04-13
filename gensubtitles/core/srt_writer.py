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


def _hex_to_pysubs2_color(hex_color: str):
    """Convert '#RRGGBB' hex string to a pysubs2.Color (alpha=0, fully opaque).

    Args:
        hex_color: A 6-digit RGB hex string, optionally prefixed with '#'
                   (e.g. '#FF8800' or 'FF8800').

    Raises:
        ValueError: If ``hex_color`` is not a valid 6-digit hex color string.
    """
    import re

    import pysubs2

    normalized = (hex_color or "").strip()
    if not re.fullmatch(r"#?[0-9a-fA-F]{6}", normalized):
        raise ValueError(
            f"Invalid hex color {hex_color!r}: expected a 6-digit RGB hex string "
            "like '#FF8800' or 'FF8800'."
        )
    h = normalized.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return pysubs2.Color(r, g, b, 0)


def _apply_ssa_style(subs: Any, style: dict) -> None:
    """Apply style dict keys to the pysubs2 SSAFile Default style."""
    s = subs.styles["Default"]
    if "fontname" in style:
        s.fontname = style["fontname"]
    if "fontsize" in style:
        s.fontsize = int(style["fontsize"])
    if "primarycolor" in style:
        s.primarycolor = _hex_to_pysubs2_color(style["primarycolor"])
    if "outlinecolor" in style:
        s.outlinecolor = _hex_to_pysubs2_color(style["outlinecolor"])


def write_ssa(
    segments: Iterable[Any],
    output_path: str | Path,
    style: dict | None = None,
) -> None:
    """
    Write SSA-formatted subtitles to a file using pysubs2.

    Args:
        segments:    Iterable of duck-typed segment objects (.start, .end, .text).
        output_path: Destination file path (str or Path). Parent dirs are created
                     automatically if they do not exist.
        style:       Optional dict with SSA style overrides: fontname, fontsize,
                     primarycolor, outlinecolor (hex strings for colors).
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

    if style:
        _apply_ssa_style(subs, style)

    subs.save(str(output_path))


def convert_srt_to_ssa(
    srt_path: str | Path,
    ssa_path: str | Path,
    style: dict | None = None,
) -> None:
    """
    Convert an existing .srt file to .ssa using pysubs2.

    Args:
        srt_path: Source SRT file path.
        ssa_path: Destination SSA file path. Parent dirs are created
                  automatically if they do not exist.
        style:    Optional dict with SSA style overrides (same keys as write_ssa).
    """
    import pysubs2

    srt_path = Path(srt_path)
    ssa_path = Path(ssa_path)
    ssa_path.parent.mkdir(parents=True, exist_ok=True)
    subs = pysubs2.SSAFile.load(str(srt_path))

    if style:
        _apply_ssa_style(subs, style)

    subs.save(str(ssa_path))


def convert_ssa_to_srt(ssa_path: str | Path, srt_path: str | Path) -> None:
    """
    Convert an existing .ssa file to .srt using pysubs2.

    Args:
        ssa_path: Source SSA file path.
        srt_path: Destination SRT file path. Parent dirs are created
                  automatically if they do not exist.
    """
    import pysubs2

    srt_path = Path(srt_path)
    srt_path.parent.mkdir(parents=True, exist_ok=True)
    subs = pysubs2.SSAFile.load(str(ssa_path))
    subs.save(str(srt_path), format_="srt")
