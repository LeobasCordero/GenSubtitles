# Phase 2: Audio Extraction Module - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.  
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Session date:** 2026-04-02  
**Phase:** 02 — Audio Extraction Module

---

## Area 1: Error Handling Granularity

**Q1:** When FFmpeg returns a non-zero exit code, what do we raise?
- Options: RuntimeError with full stderr / **Custom AudioExtractionError(RuntimeError)** / subprocess.CalledProcessError
- **Selected:** Custom `AudioExtractionError(RuntimeError)`

**Q2:** Where should AudioExtractionError be defined?
- Options: **Shared exceptions.py module** / Define in core/audio.py only / Per-module exceptions
- **Selected:** Shared `gensubtitles/exceptions.py` module

**Q3:** How granular should error discrimination be?
- Options: **Single catch-all (non-zero return code)** / Parse stderr for specific conditions / NoAudioTrackError subtype
- **Selected:** Single catch-all with full stderr in message

---

## Area 2: FFmpeg Check Placement

**Q1:** Keep import-time check or move?
- Options: **Keep at import time (current stub)** / Move to first function call / Remove entirely
- **Selected:** Keep at import time

**Q2:** Should extract_audio() enforce a subprocess timeout?
- Options: Add timeout / **No timeout in this phase**
- **Selected:** No timeout (YAGNI)

---

## Area 3: Temp-File Context Manager Design

**Q1:** Which temp-file approach for audio_temp_context()?
- Options: NamedTemporaryFile(delete=False) / **tempfile.mkstemp()** / tempfile.TemporaryDirectory()
- **Selected:** `tempfile.mkstemp()`

**Q2:** How should audio_temp_context() be implemented?
- Options: **@contextmanager generator function** / Class-based context manager / Just a helper function
- **Selected:** `@contextmanager` generator function

---

## Area 4: Test Approach

**Q1:** How should the Phase 2 unit test validate extract_audio()?
- Options: **Generate synthetic test video via FFmpeg in fixture** / Checked-in fixture file / Mock subprocess.run
- **Selected:** Generate synthetic video via FFmpeg

**Q2:** Where should the synthetic video fixture live?
- Options: **conftest.py session-scoped fixture** / setup_module() in test_audio.py / Inline in each test
- **Selected:** `conftest.py` session-scoped pytest fixture

---

*Logged: 2026-04-02*
