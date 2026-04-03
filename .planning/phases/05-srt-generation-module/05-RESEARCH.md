# Phase 5: SRT Generation Module — Research

**Phase:** 05 — srt-generation-module  
**Researcher:** gsd-planner (inline — agents not installed)  
**Date:** 2026-04-03  
**Status:** RESEARCH COMPLETE

---

## Summary

Phase 5 is a Low-complexity, well-bounded module. The `srt` library is already pinned at `>=3.5.3` in `requirements.txt`, all implementation decisions are locked in CONTEXT.md, and the test pattern (SimpleNamespace duck-typing) is established in Phase 4. No external integrations, no new dependencies, no architectural decisions remain open.

**Discovery level applied:** Level 0 (all patterns established, all dependencies present)

---

## srt Library API (v3.5.x)

### Core Classes and Functions

```python
import srt
from datetime import timedelta

# Subtitle constructor
srt.Subtitle(
    index: int,           # 1-based, required
    start: timedelta,     # required
    end: timedelta,       # required
    content: str,         # required — the subtitle text
    proprietary: str = "" # optional — rarely used
)

# Compose list of Subtitle objects into SRT-formatted string
srt.compose(
    subtitles: Iterable[Subtitle],
    reindex: bool = True,
    start_index: int = 1,
    strict: bool = True,
    eol: str | None = None
) -> str

# Parse SRT string back to generator of Subtitle objects (for test round-trips)
srt.parse(srt_string: str) -> Generator[Subtitle, None, None]
```

### Timecode Conversion Pattern

```python
from datetime import timedelta

# Segment has .start and .end as float seconds
start_td = timedelta(seconds=seg.start)   # e.g. 0.0  → timedelta(0)
end_td   = timedelta(seconds=seg.end)     # e.g. 3.5  → timedelta(seconds=3, microseconds=500000)

# srt.compose() formats these as: 00:00:00,000 --> 00:00:03,500
```

### SRT Output Format

```
1
00:00:00,000 --> 00:00:03,500
Hello world

2
00:00:04,000 --> 00:00:07,200
Second subtitle

```
- Entries separated by blank line
- Comma separator for milliseconds (not dot)
- `srt.compose()` handles all formatting — never manually format

### Empty Input Behavior

`srt.compose([])` returns an empty string `""`. Writing this to a file produces a 0-byte file, which is valid for the empty-segment case.

---

## Implementation Patterns (from codebase)

### Module Header (from transcriber.py / translator.py)

```python
"""
gensubtitles.core.srt_writer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
SRT file generation using the `srt` library.

Provides:
    segments_to_srt(segments) -> str
    write_srt(segments, output_path: str | Path) -> None
"""
from __future__ import annotations

import logging
from datetime import timedelta
from pathlib import Path

logger = logging.getLogger(__name__)
```

### Established Patterns

- `from __future__ import annotations` — top of every core module
- `logger = logging.getLogger(__name__)` — module-level logger
- `pathlib.Path` for all file path handling
- Built-in exceptions only — no new custom exception classes
- `str | Path` union type for output_path (D-02)

---

## Test Patterns (from Phase 4 translator tests)

### Segment Duck-Typing Fixture

```python
from types import SimpleNamespace

def _make_segment(start: float, end: float, text: str):
    """Minimal duck-typed segment stub matching faster-whisper/Argos output."""
    return SimpleNamespace(start=start, end=end, text=text)
```

### Round-Trip Verification Pattern

```python
import srt
from datetime import timedelta

result = segments_to_srt(segments)
parsed = list(srt.parse(result))

assert len(parsed) == len(segments)
# Timestamps match within 1ms (timedelta precision)
assert abs(parsed[0].start - timedelta(seconds=segments[0].start)) < timedelta(milliseconds=1)
```

### Edge Cases to Cover (D-03: ~12–15 tests)

| Test | Purpose |
|------|---------|
| Basic segment → SRT string | UAT-1 |
| Leading/trailing whitespace stripped | UAT-2 |
| `write_srt` creates file readable by `srt.parse()` | UAT-3 |
| Round-trip count and timestamp integrity | UAT-4 |
| Empty segment list → no exception, file created | UAT-5 |
| Multi-line text (newline in `.text`) | SRT-04 integrity |
| Unicode: Arabic text | UTF-8 correctness |
| Unicode: CJK characters | UTF-8 correctness |
| Timestamps > 1 hour (e.g. 3723.0 sec → `01:02:03,000`) | SRT-02 |
| Deeply nested output directory (`output/sub/dir/test.srt`) | SRT-03 parent mkdir |
| Whitespace-only text (e.g. `"   "`) | stripped → `""` content |
| `write_srt` with Path object (not str) | D-02 str \| Path |
| `write_srt` with str path | D-02 str \| Path |
| Warning logged on empty segments | logging behavior |

---

## Validation Architecture

### Automated Validation Strategy

The following automated checks validate the SRT module against all 4 requirements:

**SRT-01** (valid SRT via `srt` library):
```bash
python -m pytest tests/test_srt_writer.py -k "test_segments_to_srt_basic or test_write_srt_parseable" -v
```
Presence of `srt.parse()` round-trip tests confirms valid SRT output.

**SRT-02** (correct timecode conversion):
```bash
python -m pytest tests/test_srt_writer.py -k "timestamp" -v
# Plus: grep "00:00:00,000 --> 00:00:03,500" output
```

**SRT-03** (configurable output path + parent dir creation):
```bash
python -m pytest tests/test_srt_writer.py -k "test_write_srt_creates_nested_directory" -v
```

**SRT-04** (text preserved as-is):
```bash
python -m pytest tests/test_srt_writer.py -k "test_text_preserved or test_unicode" -v
```

**Full suite:**
```bash
python -m pytest tests/test_srt_writer.py -v
```
All tests must pass. No mocking of `srt` library — it is a real (lightweight) dependency.

---

## Key Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| `srt.compose("")` for empty list | Returns `""` — write directly, no special case needed |
| Timestamp rounding (float precision) | `timedelta(seconds=float)` handles it; round-trip test validates within 1ms |
| Parent directory creation race | `mkdir(parents=True, exist_ok=True)` is idempotent |
| Non-UTF-8 characters in text | `write_open(file, "w", encoding="utf-8")` handles any Unicode |

---

## ## RESEARCH COMPLETE

Phase 5 is ready for planning. All decisions are locked (D-01 to D-03), the `srt` library API is confirmed, patterns are established. Single combined plan (05-01-PLAN.md) as per D-01.
