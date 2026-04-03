"""
Phase 5 SRT generation tests — covers SRT-01 through SRT-04.
Uses SimpleNamespace to duck-type segment objects (mirrors faster-whisper/Argos output).
"""
from __future__ import annotations

import srt
import pytest
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

from gensubtitles.core.srt_writer import segments_to_srt, write_srt


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


def test_text_stripped_leading_trailing_whitespace(tmp_path):
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
