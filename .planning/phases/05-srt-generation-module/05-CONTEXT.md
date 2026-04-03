# Phase 5: SRT Generation Module - Context

**Gathered:** 2026-04-03  
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement `gensubtitles/core/srt_writer.py` with two public functions: `segments_to_srt` and `write_srt`. Converts duck-typed segment objects (`.start`, `.end`, `.text`) into a valid `.srt` file using the `srt` library. No pipeline wiring, CLI flags, or API endpoints belong here — this phase delivers `core/srt_writer.py` and its test suite only.

</domain>

<decisions>
## Implementation Decisions

### Plan Structure
- **D-01:** 1 combined plan — implementation + tests in a single `05-01-PLAN.md`. Phase complexity is low enough that splitting would add overhead without benefit.

### Function Signatures
- **D-02:** `write_srt` accepts `str | Path` for `output_path` — internally converts with `Path(output_path)`. More ergonomic for Phase 6 pipeline callers that use `pathlib.Path` throughout, no breaking changes.
- Signature: `write_srt(segments, output_path: str | Path) -> None`
- Signature: `segments_to_srt(segments) -> str`

### Test Coverage
- **D-03:** Standard depth — ~12–15 tests covering the 5 ROADMAP UAT criteria plus edge cases: multi-line text, Unicode content (Arabic, CJK), timestamps > 1 hour, deeply nested output directory path (`output/sub/dir/test.srt`), whitespace-only text handling.

### Agent's Discretion
- Exact warning mechanism for empty segment list (Python `logging` module, consistent with other core modules)
- Whether to add a module-level `logger = logging.getLogger(__name__)` (established pattern — should follow it)
- Test fixture design for mock segment objects (simple `SimpleNamespace` or namedtuple to duck-type `.start`, `.end`, `.text`)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — SRT-01, SRT-02, SRT-03, SRT-04

### Roadmap
- `.planning/ROADMAP.md` — Phase 5 plans and UAT criteria

### Prior Phase Contexts
- `.planning/phases/04-translation-engine/04-CONTEXT.md` — D-07/D-08 (segment duck-type contract: `.start`, `.end`, `.text`)
- `.planning/phases/02-audio-extraction-module/02-CONTEXT.md` — D-01 to D-04 (exception patterns)

No external specs — all decisions captured above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `gensubtitles/core/srt_writer.py` — Phase 1 stub: single comment line. Phase 5 replaces with full implementation.
- `gensubtitles/core/transcriber.py` — reference for module structure: `from __future__ import annotations`, module-level `logger`, namedtuple usage.
- `gensubtitles/core/translator.py` — reference for logging pattern and `pathlib.Path` usage.

### Established Patterns
- `from __future__ import annotations` at top of all core modules.
- `logger = logging.getLogger(__name__)` module-level logger — follow in `srt_writer.py`.
- Built-in exceptions only — no new custom exception classes (D-01 from Phase 4).
- `pathlib.Path` for all file path handling.

### Integration Points
- `srt_writer.py` is consumed by Phase 6 `core/pipeline.py` — `write_srt(segments, output_path)` is the final pipeline stage.
- Segments passed in are duck-typed objects with `.start` (float, seconds), `.end` (float, seconds), `.text` (str) — produced by Phase 3 transcriber or Phase 4 translator.

</code_context>

<specifics>
## Specific Ideas

No specific references or "I want it like X" moments — implementation is well-specified in ROADMAP.md plans.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 05-srt-generation-module*  
*Context gathered: 2026-04-03*
