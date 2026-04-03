# Phase 6: Core Pipeline Assembly - Context

**Gathered:** 2026-04-03  
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire `audio.py`, `transcriber.py`, `translator.py`, and `srt_writer.py` into a single callable `run_pipeline()` function in `gensubtitles/core/pipeline.py`. Defines `PipelineResult` dataclass. Manages temp file lifecycle and progress callbacks. No CLI flags, no API endpoints, no model caching — those belong to Phases 7 and 8.

Also includes a targeted update to Phase 3 (`core/transcriber.py` and `tests/test_transcriber.py`) to extend `TranscriptionResult` with a `duration` field (per D-03).

</domain>

<decisions>
## Implementation Decisions

### Transcriber Construction
- **D-01:** `run_pipeline` accepts `model_size` and `device` parameters only — always constructs a fresh `WhisperTranscriber` internally. No pre-loaded transcriber parameter on `run_pipeline`. Phase 8 (FastAPI) will handle model reuse at the API layer using its own `lifespan`-loaded model and calling transcribe directly or via a different entry point.

### Progress Callback
- **D-02:** The progress callback is always called exactly 4 times with `total=4`, regardless of whether translation is skipped. When `target_lang=None`, emit `("Translation skipped", 3, 4)` instead of `("Translating", 3, 4)`. The CLI (Phase 7) may choose to display or suppress that line — that's the CLI's concern.
  - Stage 1: `("Extracting audio", 1, 4)`
  - Stage 2: `("Transcribing", 2, 4)`
  - Stage 3: `("Translating", 3, 4)` OR `("Translation skipped", 3, 4)` when `target_lang=None`
  - Stage 4: `("Writing SRT", 4, 4)`

### `audio_duration_seconds` Source
- **D-03:** Extend `TranscriptionResult` namedtuple in `core/transcriber.py` to add a `duration` field — `TranscriptionResult = namedtuple("TranscriptionResult", ["segments", "language", "duration"])`. The `info.duration` value is already returned by `faster_whisper`'s `model.transcribe()` as part of `TranscriptionInfo`. Phase 6 plan must update `transcriber.py` and `tests/test_transcriber.py` (the 25-test suite) to accommodate the new field. `PipelineResult.audio_duration_seconds` reads from `result.duration`.

### Agent's Discretion
- `PipelineError` design — follow the existing `exceptions.py` pattern (subclass `GenSubtitlesError` / `RuntimeError`). Planner decides whether to include a `stage` attribute or just embed the stage name in the message.
- `core/__init__.py` exports — whether to expose `run_pipeline` and `PipelineResult` from the package `__init__` is at planner's discretion; consistency with existing `__init__.py` (minimal exports) should guide the choice.
- Input validation strictness — roadmap specifies `Path.is_file()` for video path and writable parent for output path; exact error message wording is at planner's discretion.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — AUD-01–04, TRN-01–06, TRANS-01–05, SRT-01–04 (integration requirements this phase satisfies)

### Roadmap
- `.planning/ROADMAP.md` — Phase 6 plans and UAT criteria

### Prior Phase Contexts
- `.planning/phases/02-audio-extraction-module/02-CONTEXT.md` — Exception patterns, `audio_temp_context()` contract
- `.planning/phases/03-transcription-engine/` — `TranscriptionResult` namedtuple (being extended in this phase)
- `.planning/phases/04-translation-engine/04-CONTEXT.md` — D-07/D-08 segment duck-type contract (`.start`, `.end`, `.text`); D-01 no new exception classes without good reason
- `.planning/phases/05-srt-generation-module/05-CONTEXT.md` — D-02 `write_srt` signature, path handling

No external specs — all decisions captured above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `gensubtitles/core/audio.py` — `extract_audio(video_path, output_path)`, `audio_temp_context()` context manager (established cleanup pattern)
- `gensubtitles/core/transcriber.py` — `WhisperTranscriber`, `transcribe_audio()`, `TranscriptionResult` namedtuple (to be extended with `duration`)
- `gensubtitles/core/translator.py` — `translate_segments(segments, source_lang, target_lang)`, `TranslatedSegment` namedtuple
- `gensubtitles/core/srt_writer.py` — `write_srt(segments, output_path: str | Path)`
- `gensubtitles/exceptions.py` — `GenSubtitlesError`, `AudioExtractionError`, `TranscriptionError` (base pattern for `PipelineError`)

### Established Patterns
- All core modules use `from __future__ import annotations`, module-level `logger = logging.getLogger(__name__)`, deferred heavy imports
- `gensubtitles/__init__.py` has only `__version__` — no core imports (D-12 anti-pattern from Phase 1)
- Exception hierarchy: domain-specific errors subclass `GenSubtitlesError(RuntimeError)` in `exceptions.py`
- `pathlib.Path` used throughout for file operations

### Integration Points
- `pipeline.py` is a new file in `gensubtitles/core/` — no stub exists yet
- `TranscriptionResult` in `transcriber.py` must gain a `duration` field — this is a breaking change to the namedtuple; all construction sites and tests need updating

</code_context>

<specifics>
## Specific Ideas

No specific UI or formatting requirements — this is a pure Python wiring phase. The roadmap plan items (items 1–8 in Phase 6) are prescriptive enough that the planner can derive tasks directly from them.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 06-core-pipeline-assembly*  
*Context gathered: 2026-04-03*
