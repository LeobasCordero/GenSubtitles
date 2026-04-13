"""
Phase 5 SRT generation tests — covers SRT-01 through SRT-04.
Uses SimpleNamespace to duck-type segment objects (mirrors faster-whisper/Argos output).
"""
from __future__ import annotations

import srt
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

from gensubtitles.core.srt_writer import (
    convert_srt_to_ssa,
    convert_ssa_to_srt,
    segments_to_srt,
    write_srt,
    write_ssa,
    _hex_to_pysubs2_color,
)


# ── helpers ───────────────────────────────────────────────────────────────────


def _make_segment(start: float, end: float, text: str):
    """Minimal segment stub with .start/.end/.text (mirrors faster-whisper Segment)."""
    return SimpleNamespace(start=start, end=end, text=text)


# ── SRT-01: valid SRT via srt library ─────────────────────────────────────────


def test_segments_to_srt_returns_string():
    """segments_to_srt() returns a str."""
    seg = _make_segment(0.0, 3.5, "Hello world")
    result = segments_to_srt([seg])
    assert isinstance(result, str)


def test_segments_to_srt_parseable():
    """Output of segments_to_srt() can be round-tripped through srt.parse() without error."""
    seg = _make_segment(0.0, 3.5, "Hello world")
    result = segments_to_srt([seg])
    parsed = list(srt.parse(result))
    assert len(parsed) == 1


# ── SRT-02: correct timecodes ─────────────────────────────────────────────────


def test_segments_to_srt_basic_timecode():
    """start=0.0, end=3.5 → output contains '00:00:00,000 --> 00:00:03,500'."""
    seg = _make_segment(0.0, 3.5, "Hello world")
    result = segments_to_srt([seg])
    assert "00:00:00,000 --> 00:00:03,500" in result


def test_segments_to_srt_timestamp_over_one_hour():
    """start=3723.0, end=3724.5 → output contains '01:02:03,000 --> 01:02:04,500'."""
    seg = _make_segment(3723.0, 3724.5, "Late subtitle")
    result = segments_to_srt([seg])
    assert "01:02:03,000 --> 01:02:04,500" in result


def test_round_trip_timestamp_integrity():
    """Parsed start timedelta matches original segment start within 1ms."""
    seg = _make_segment(3723.0, 3724.5, "Late subtitle")
    result = segments_to_srt([seg])
    parsed = list(srt.parse(result))
    delta = abs(parsed[0].start - timedelta(seconds=seg.start))
    assert delta.total_seconds() < 0.001


# ── SRT-03: configurable output path ─────────────────────────────────────────


def test_write_srt_creates_file(tmp_path):
    """write_srt() creates the output file at the given path."""
    seg = _make_segment(0.0, 3.5, "Hello world")
    out = tmp_path / "test.srt"
    write_srt([seg], out)
    assert out.exists()


def test_write_srt_file_is_utf8(tmp_path):
    """The output file can be read as UTF-8 without error."""
    seg = _make_segment(0.0, 3.5, "Hello world")
    out = tmp_path / "test.srt"
    write_srt([seg], out)
    out.read_text(encoding="utf-8")  # must not raise


def test_write_srt_parseable(tmp_path):
    """The output file content can be parsed by srt.parse() and yields correct count."""
    segs = [_make_segment(0.0, 1.0, "One"), _make_segment(1.5, 2.5, "Two")]
    out = tmp_path / "test.srt"
    write_srt(segs, out)
    content = out.read_text(encoding="utf-8")
    parsed = list(srt.parse(content))
    assert len(parsed) == len(segs)


def test_write_srt_str_path(tmp_path):
    """write_srt() accepts a str path (D-02: str | Path)."""
    seg = _make_segment(0.0, 3.5, "Hello world")
    out = str(tmp_path / "str_test.srt")
    write_srt([seg], out)
    assert Path(out).exists()


def test_write_srt_creates_nested_directory(tmp_path):
    """write_srt() creates parent directories automatically."""
    seg = _make_segment(0.0, 3.5, "Hello world")
    out = tmp_path / "sub" / "dir" / "out.srt"
    write_srt([seg], out)
    assert out.exists()


# ── SRT-04: text preserved ────────────────────────────────────────────────────


def test_text_stripped_leading_trailing_whitespace():
    """Leading/trailing whitespace is stripped from segment text (UAT-2)."""
    seg = _make_segment(0.0, 3.5, "  Hello world  ")
    result = segments_to_srt([seg])
    parsed = list(srt.parse(result))
    assert parsed[0].content == "Hello world"


def test_unicode_arabic(tmp_path):
    """Arabic text is preserved correctly in the SRT file."""
    seg = _make_segment(0.0, 3.5, "مرحبا")
    out = tmp_path / "arabic.srt"
    write_srt([seg], out)
    content = out.read_text(encoding="utf-8")
    assert "مرحبا" in content


def test_unicode_cjk(tmp_path):
    """CJK (Chinese/Japanese/Korean) text is preserved correctly in the SRT file."""
    seg = _make_segment(0.0, 3.5, "你好世界")
    out = tmp_path / "cjk.srt"
    write_srt([seg], out)
    content = out.read_text(encoding="utf-8")
    assert "你好世界" in content


# ── Edge cases ───────────────────────────────────────────────────────────────


def test_empty_segments_no_exception(tmp_path):
    """write_srt() with empty segment list does not raise, and creates the file (UAT-5)."""
    out = tmp_path / "empty.srt"
    write_srt([], out)
    assert out.exists()


# ── SSA write/convert tests ──────────────────────────────────────────────────


def test_write_ssa_creates_file(tmp_path):
    """write_ssa() creates a .ssa file at the given path."""
    seg = _make_segment(0.0, 3.5, "Hello world")
    out = tmp_path / "test.ssa"
    write_ssa([seg], out)
    assert out.exists()


def test_write_ssa_creates_nested_directory(tmp_path):
    """write_ssa() creates parent directories automatically."""
    seg = _make_segment(0.0, 3.5, "Hello world")
    out = tmp_path / "sub" / "dir" / "out.ssa"
    write_ssa([seg], out)
    assert out.exists()


def test_convert_srt_to_ssa_round_trip(tmp_path):
    """convert_srt_to_ssa() produces a valid .ssa file from an SRT file."""
    seg = _make_segment(0.0, 3.5, "Hello world")
    srt_file = tmp_path / "input.srt"
    write_srt([seg], srt_file)

    ssa_file = tmp_path / "output.ssa"
    convert_srt_to_ssa(srt_file, ssa_file)
    assert ssa_file.exists()
    content = ssa_file.read_text(encoding="utf-8")
    assert "Hello world" in content


def test_convert_ssa_to_srt_round_trip(tmp_path):
    """convert_ssa_to_srt() produces a valid .srt file from an SSA file."""
    seg = _make_segment(0.0, 3.5, "Hello world")
    ssa_file = tmp_path / "input.ssa"
    write_ssa([seg], ssa_file)

    srt_file = tmp_path / "output.srt"
    convert_ssa_to_srt(ssa_file, srt_file)
    assert srt_file.exists()
    content = srt_file.read_text(encoding="utf-8")
    parsed = list(srt.parse(content))
    assert len(parsed) == 1
    assert "Hello world" in parsed[0].content


def test_convert_srt_to_ssa_creates_parent_dirs(tmp_path):
    """convert_srt_to_ssa() creates destination parent dirs if they don't exist."""
    seg = _make_segment(0.0, 3.5, "Hello world")
    srt_file = tmp_path / "input.srt"
    write_srt([seg], srt_file)

    ssa_file = tmp_path / "new" / "dir" / "output.ssa"
    convert_srt_to_ssa(srt_file, ssa_file)
    assert ssa_file.exists()


def test_convert_ssa_to_srt_creates_parent_dirs(tmp_path):
    """convert_ssa_to_srt() creates destination parent dirs if they don't exist."""
    seg = _make_segment(0.0, 3.5, "Hello world")
    ssa_file = tmp_path / "input.ssa"
    write_ssa([seg], ssa_file)

    srt_file = tmp_path / "new" / "dir" / "output.srt"
    convert_ssa_to_srt(ssa_file, srt_file)
    assert srt_file.exists()


def test_srt_to_ssa_to_srt_preserves_text(tmp_path):
    """Full round-trip SRT → SSA → SRT preserves subtitle text."""
    seg = _make_segment(1.5, 4.0, "Round trip test")
    srt_file = tmp_path / "original.srt"
    write_srt([seg], srt_file)

    ssa_file = tmp_path / "intermediate.ssa"
    convert_srt_to_ssa(srt_file, ssa_file)

    srt_back = tmp_path / "restored.srt"
    convert_ssa_to_srt(ssa_file, srt_back)

    content = srt_back.read_text(encoding="utf-8")
    parsed = list(srt.parse(content))
    assert len(parsed) == 1
    assert "Round trip test" in parsed[0].content


# ── Style parameter tests (STYLE-01 through STYLE-05) ────────────────────────


def test_write_ssa_default_style(tmp_path):
    """write_ssa() with no style arg produces a valid SSA file."""
    import pysubs2
    seg = _make_segment(0.0, 3.5, "Hello world")
    out = tmp_path / "test.ssa"
    write_ssa([seg], out)
    subs = pysubs2.SSAFile.load(str(out))
    assert "Default" in subs.styles


def test_write_ssa_custom_fontname(tmp_path):
    """write_ssa() with style fontname applies it to SSA Default style."""
    import pysubs2
    seg = _make_segment(0.0, 3.5, "Hello world")
    out = tmp_path / "test.ssa"
    style = {"fontname": "Verdana", "fontsize": 20, "primarycolor": "#FFFFFF", "outlinecolor": "#000000"}
    write_ssa([seg], out, style=style)
    subs = pysubs2.SSAFile.load(str(out))
    assert subs.styles["Default"].fontname == "Verdana"


def test_write_ssa_custom_fontsize(tmp_path):
    """write_ssa() with style fontsize applies it to SSA Default style."""
    import pysubs2
    seg = _make_segment(0.0, 3.5, "Hello world")
    out = tmp_path / "test.ssa"
    style = {"fontname": "Arial", "fontsize": 36, "primarycolor": "#FFFFFF", "outlinecolor": "#000000"}
    write_ssa([seg], out, style=style)
    subs = pysubs2.SSAFile.load(str(out))
    assert subs.styles["Default"].fontsize == 36


def test_write_ssa_custom_colors(tmp_path):
    """write_ssa() with style colors applies primarycolor and outlinecolor (ASS format preserves both)."""
    import pysubs2
    seg = _make_segment(0.0, 3.5, "Hello world")
    out = tmp_path / "test.ass"
    style = {"fontname": "Arial", "fontsize": 20, "primarycolor": "#FF0000", "outlinecolor": "#0000FF"}
    write_ssa([seg], out, style=style)
    subs = pysubs2.SSAFile.load(str(out))
    assert subs.styles["Default"].primarycolor.r == 255
    assert subs.styles["Default"].outlinecolor.b == 255


def test_convert_srt_to_ssa_with_style(tmp_path):
    """convert_srt_to_ssa() with style applies fontname to SSA Default style."""
    import pysubs2
    seg = _make_segment(0.0, 3.5, "Hello world")
    srt_file = tmp_path / "input.srt"
    write_srt([seg], srt_file)
    ssa_file = tmp_path / "output.ssa"
    style = {"fontname": "Tahoma", "fontsize": 20, "primarycolor": "#FFFFFF", "outlinecolor": "#000000"}
    convert_srt_to_ssa(srt_file, ssa_file, style=style)
    subs = pysubs2.SSAFile.load(str(ssa_file))
    assert subs.styles["Default"].fontname == "Tahoma"


# ── _hex_to_pysubs2_color validation tests ────────────────────────────────────


def test_hex_to_pysubs2_color_with_hash():
    """_hex_to_pysubs2_color() accepts '#RRGGBB' strings."""
    color = _hex_to_pysubs2_color("#FF8800")
    assert color.r == 0xFF
    assert color.g == 0x88
    assert color.b == 0x00


def test_hex_to_pysubs2_color_without_hash():
    """_hex_to_pysubs2_color() accepts 'RRGGBB' strings without '#'."""
    color = _hex_to_pysubs2_color("00FF00")
    assert color.g == 0xFF


def test_hex_to_pysubs2_color_uppercase_and_lowercase():
    """_hex_to_pysubs2_color() is case-insensitive."""
    assert _hex_to_pysubs2_color("#aabbcc").r == 0xAA
    assert _hex_to_pysubs2_color("#AABBCC").r == 0xAA


def test_hex_to_pysubs2_color_strips_whitespace():
    """_hex_to_pysubs2_color() strips surrounding whitespace."""
    color = _hex_to_pysubs2_color("  #FF0000  ")
    assert color.r == 0xFF


def test_hex_to_pysubs2_color_invalid_empty_raises():
    """_hex_to_pysubs2_color() raises ValueError for empty string."""
    import pytest
    with pytest.raises(ValueError, match="Invalid hex color"):
        _hex_to_pysubs2_color("")


def test_hex_to_pysubs2_color_invalid_short_raises():
    """_hex_to_pysubs2_color() raises ValueError for shorthand hex (#RGB)."""
    import pytest
    with pytest.raises(ValueError, match="Invalid hex color"):
        _hex_to_pysubs2_color("#FFF")


def test_hex_to_pysubs2_color_invalid_non_hex_raises():
    """_hex_to_pysubs2_color() raises ValueError for non-hex characters."""
    import pytest
    with pytest.raises(ValueError, match="Invalid hex color"):
        _hex_to_pysubs2_color("#GGGGGG")
