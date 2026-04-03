# Phase 2: Audio Extraction Module - Context

**Gathered:** 2026-04-02  
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement FFmpeg-based audio extraction that takes any supported video format and outputs a 16kHz mono WAV file suitable for Whisper. No transcription, translation, or SRT logic belongs here — this phase delivers `core/audio.py` with extraction, temp-file management, and error handling only.

</domain>

<decisions>
## Implementation Decisions

### Error Handling
- **D-01:** Introduce `AudioExtractionError(RuntimeError)` as the canonical exception for FFmpeg failures and missing audio track conditions
- **D-02:** `AudioExtractionError` is defined in `gensubtitles/exceptions.py` — a **shared exceptions module** (not in `core/audio.py`) so downstream modules can import it without circular dependencies
- **D-03:** Error discrimination is **single catch-all** — any non-zero FFmpeg return code raises `AudioExtractionError` with the full `stderr` text. Callers parse the message if they need specifics. No separate `NoAudioTrackError` subtype.
- **D-04:** `ValueError` (built-in) is raised for unsupported file extensions before any subprocess is spawned — consistent with Phase 1 "use built-in exceptions where possible" pattern

### FFmpeg Availability Check
- **D-05:** The `shutil.which("ffmpeg")` check remains **at import time** in `core/audio.py` (the Phase 1 stub is already in place — keep it). Raises `EnvironmentError` with install instructions.
- **D-06:** No subprocess timeout added in this phase — deferred to a future phase if needed (YAGNI)

### Temp-File Context Manager
- **D-07:** `audio_temp_context()` uses **`tempfile.mkstemp(suffix=".wav")`** to create the temp file — returns (fd, path); fd is closed immediately after creation, path is yielded
- **D-08:** Implemented as a **`@contextmanager` generator function** (not a class). Deletes the temp file in the `finally` block via `Path(path).unlink(missing_ok=True)`
- **D-09:** Returns a `pathlib.Path` (not a raw string) from the context manager yield — consistent with modern Python style

### Test Strategy
- **D-10:** Unit tests use a **`conftest.py` session-scoped pytest fixture** that generates a synthetic 1-second test video via FFmpeg (`lavfi` source, no input file needed). Video is created once per test run and reused across all audio tests.
- **D-11:** No checked-in binary fixtures — keeps the repo clean; no subprocess mocking — ensures the real FFmpeg command is validated end-to-end
- **D-12:** Test file is `tests/test_audio.py`; fixture lives in `tests/conftest.py`

### the Agent's Discretion
- Exact FFmpeg lavfi filter string for synthetic video generation (e.g., `ffmpeg -f lavfi -i "testsrc=duration=1:size=320x240:rate=1" -f lavfi -i "sine=frequency=440:duration=1" -c:v libx264 -c:a aac output.mp4`) — planner picks the right incantation
- Exact `PATH`-style hint in `EnvironmentError` message wording (minor copy)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — AUD-01, AUD-02, AUD-03, AUD-04 (the requirements this phase satisfies)

### Roadmap
- `.planning/ROADMAP.md` Phase 2 plans and UAT criteria

### Prior Phase Context
- `.planning/phases/01-project-infrastructure/01-CONTEXT.md` — D-09/D-10/D-11 (import-time FFmpeg check already in stub), D-12 (package layout), D-14 (root main.py shim)

No external specs beyond the above — all decisions captured in `<decisions>` above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `gensubtitles/core/audio.py` — Phase 1 stub: import-time `shutil.which("ffmpeg")` check already in place. Phase 2 adds the implementation below the stub comment.
- `tests/test_infrastructure.py` — existing test file; Phase 2 adds `tests/test_audio.py` alongside it
- `tests/conftest.py` — does not exist yet; Phase 2 creates it with the synthetic video fixture

### Established Patterns
- Built-in Python exceptions used by preference (Phase 1 decisions) — Phase 2 introduces first custom exception (`AudioExtractionError`) as a `RuntimeError` subclass
- `pathlib.Path` preferred over raw strings for file paths (modern Python style per project baseline)

### Integration Points
- `gensubtitles/exceptions.py` — new file; imported by `core/audio.py` and will be imported by future core modules (`transcriber.py`, `translator.py`, `srt_writer.py`)
- `core/audio.py` is imported by the pipeline (Phase 6), CLI (Phase 7), and FastAPI route (Phase 8)

</code_context>

<specifics>
## Specific Ideas

- The `exceptions.py` shared module was explicitly chosen to avoid future circular imports — downstream modules in Phases 3–8 can freely import from it
- Synthetic FFmpeg test video generated via `lavfi` avoids any binary checked into the repo

</specifics>

<deferred>
## Deferred Ideas

- subprocess timeout for extract_audio() — mentioned during discussion, deferred to a future phase (YAGNI for Phase 2)
- `NoAudioTrackError` as a separate exception subtype — rejected in favor of single catch-all; revisit if callers need programmatic distinction in Phase 6+

</deferred>

---

*Phase: 02-audio-extraction-module*  
*Context gathered: 2026-04-02*
