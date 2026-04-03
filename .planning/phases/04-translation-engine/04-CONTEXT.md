# Phase 4: Translation Engine - Context

**Gathered:** 2026-04-03  
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement optional offline translation using Argos Translate that installs language model packages on first use, caches them locally, and skips translation when source language equals target language. No pipeline wiring, CLI flags, or API endpoints belong here — this phase delivers `core/translator.py` only.

</domain>

<decisions>
## Implementation Decisions

### Exception Design
- **D-01:** No new custom exception class — reuse built-in Python exceptions only (consistent choice, not following the AudioExtractionError/TranscriptionError pattern).
- **D-02:** `ValueError` is raised for unsupported language pairs (both not installed and not available remotely), with the pair name in the message. Already required by TRANS-04 and the roadmap plan.
- **D-03:** `RuntimeError` is raised for install or download failures that leave the pair unavailable after best-effort network attempt.

### Network Failure Behavior
- **D-04:** Best-effort approach — `update_package_index()` is called first; if it fails (no internet), log a warning and fall back to whatever is already cached.
- **D-05:** If the pair IS already installed after a failed index update, proceed with translation silently (no error).
- **D-06:** If the pair is NOT installed and the network call failed, raise `RuntimeError` explaining that the model could not be downloaded and the pair is not cached.

### Translated Segment Type
- **D-07:** No new type is introduced. When `source_lang == target_lang`, return the original segment objects unchanged (same references).
- **D-08:** When translation occurs, the agent picks the cleanest approach that preserves `.start`, `.end`, `.text` attribute access for downstream SRT generation — exact mechanism (namedtuple replacement, simple object, etc.) is at the planner's discretion.

### Progress / Logging During Model Download
- **D-09:** Print directly to stdout so downloads are always visible (CLI and API alike).
- **D-10:** Use `tqdm` for download progress — show a progress bar during model package download. Planner must verify `tqdm` is in `requirements.txt`; add it if missing.
- **D-11:** Log a warning via Python `logging` when `update_package_index()` fails (offline fallback message).

### Agent's Discretion
- Exact format for translated segment replacement (namedtuple, dataclass, or attribute-compatible object) — planner picks the cleanest approach that satisfies `.start`, `.end`, `.text` duck-typing required by Phase 5 SRT writer.
- Exact tqdm integration with argostranslate download callback (argostranslate may not expose a direct progress hook — planner investigates best approach).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — TRANS-01, TRANS-02, TRANS-03, TRANS-04, TRANS-05 (the requirements this phase satisfies)

### Roadmap
- `.planning/ROADMAP.md` — Phase 4 plans and UAT criteria

### Prior Phase Context
- `.planning/phases/02-audio-extraction-module/02-CONTEXT.md` — D-01 to D-04 (exception patterns, shared exceptions.py module)

No external specs beyond the above — all decisions captured in `<decisions>` above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `gensubtitles/core/translator.py` — Phase 1 stub: single comment line. Phase 4 adds full implementation.
- `gensubtitles/exceptions.py` — shared exceptions module; Phase 4 does NOT add a new exception here (D-01 decision).
- `gensubtitles/core/transcriber.py` — reference for module structure, logging setup, and namedtuple usage pattern.

### Established Patterns
- Module-level `logger = logging.getLogger(__name__)` — established in transcriber.py, follow in translator.py.
- `from __future__ import annotations` at top of core modules.
- `pathlib.Path` for file paths, but translator.py may not need paths directly.
- Built-in exceptions preferred (D-01 locks this for Phase 4).

### Integration Points
- `gensubtitles/core/translator.py` is consumed by the pipeline (Phase 6), CLI flags `--target-lang` (Phase 7), and FastAPI `GET /languages` + `POST /subtitles` (Phases 8–9).
- The translated segment contract (`.start`, `.end`, `.text`) must be satisfied for Phase 5's `srt_writer.py` to consume output.

</code_context>

<specifics>
## Specific Ideas

No specific references or "I want it like X" moments — open to standard Argos Translate patterns.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 04-translation-engine*  
*Context gathered: 2026-04-03*
