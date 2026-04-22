# Phase 12: Retroactive Verification + Pipeline Refactor - Context

**Gathered:** 2026-04-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Two deliverables:

1. **Documentation** — Write VERIFICATION.md formal exit records for Phase 06 (Core Pipeline Assembly) and Phase 07 (CLI Interface). Same pattern as Phase 11: compile evidence from UAT.md + summaries, no test re-run.

2. **Code refactor** — Close Integration Gap #1:
   - Add optional `transcriber: Optional[WhisperTranscriber] = None` to `run_pipeline()` in `core/pipeline.py`
   - Add optional `cancel_event: Optional[threading.Event] = None` to `run_pipeline()` — check after each stage and return early if set
   - Replace `_run_pipeline_job()` inline pipeline logic in `api/routers/subtitles.py` with a thin wrapper that calls `run_pipeline()`, bridging SSE progress via a callback closure and passing the job's cancel event

Phases in scope for documentation: 06, 07.
No VALIDATION.md files exist in phases 06 or 07 — nothing to delete.

</domain>

<decisions>
## Implementation Decisions

### Inherited from Phase 11

- **D-01:** Compile evidence from existing artifacts only (UAT.md, plan summaries, code inspection). No test re-run required.
- **D-02:** File-level evidence citation — cite test file name (e.g. `tests/test_pipeline.py`) rather than individual test function names.
- **D-05:** Follow the same YAML front-matter + evidence table structure established in `10-VERIFICATION.md`. Front-matter keys: `phase`, `status`, `verified`, `verification_method`, `score`.

### Phase 12 Specific

- **D-06 (Area 1):** Replace `_run_pipeline_job()` inline logic entirely. `run_pipeline()` gains a `cancel_event: Optional[threading.Event] = None` parameter. After each stage (audio extraction, transcription, translation), check `cancel_event` and raise or return early if set. `_run_pipeline_job()` becomes a thin wrapper: create a `progress_callback` closure that updates SSE events, call `run_pipeline(transcriber=..., cancel_event=job["cancel"])`, handle result/error.

- **D-07 (Area 2):** `transcriber` parameter is purely optional with fallback: `transcriber: Optional[WhisperTranscriber] = None`. If None, `run_pipeline()` creates `WhisperTranscriber(model_size=model_size, device=device)` as it does today. CLI path is completely unchanged.

- **D-08 (Area 3):** API-01..04 are verified in Phase 12's own VERIFICATION.md only (not in Phase 06 or 07). Phase 06 VERIFICATION.md covers pipeline integration requirements; Phase 07 VERIFICATION.md covers CLI-01..04.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Verification Format Reference
- `.planning/phases/10-documentation-end-to-end-validation/10-VERIFICATION.md` — Canonical VERIFICATION.md format.

### Phase 06 Evidence Sources
- `.planning/phases/06-core-pipeline-assembly/06-UAT.md` — UAT results (5 tests, all pass)
- `.planning/phases/06-core-pipeline-assembly/06-01-SUMMARY.md`, `06-02-SUMMARY.md`

### Phase 07 Evidence Sources
- `.planning/phases/07-cli-interface/07-UAT.md` — UAT results (6 tests, all pass; CLI-01 to CLI-04 requirement coverage)
- `.planning/phases/07-cli-interface/07-01-SUMMARY.md`, `07-02-SUMMARY.md`

### Code Files to Modify
- `gensubtitles/core/pipeline.py` — Add `transcriber=None`, `cancel_event=None` params to `run_pipeline()`
- `gensubtitles/api/routers/subtitles.py` — Replace `_run_pipeline_job()` inline logic with `run_pipeline()` delegation

### Test File
- `tests/test_pipeline.py` — Add tests for `transcriber=` injection and `cancel_event=` short-circuit

</canonical_refs>

<code_context>
## Existing Code Insights

### run_pipeline() current signature
```python
def run_pipeline(
    video_path: Path | str,
    output_path: Path | str,
    *,
    model_size: str = "medium",
    target_lang: str | None = None,
    source_lang: str | None = None,
    device: str = "auto",
    progress_callback: Callable | None = None,
    engine: str = "argos",
) -> PipelineResult:
```
Stage structure: extract_audio → transcribe → translate (conditional) → write_srt
Currently creates `WhisperTranscriber(model_size=model_size, device=device)` internally.

### _run_pipeline_job() current design
Receives `transcriber: WhisperTranscriber` from `get_transcriber()` FastAPI dependency (preloaded at lifespan).
Manually orchestrates: extract_audio → transcriber.transcribe → translate_segments → write_srt.
Has per-stage cancel checks via `job["cancel"].is_set()` (threading.Event).
Uses `_set_progress(stage, label, current, total, job=job)` for SSE streaming.

### After refactor
`_run_pipeline_job()` becomes:
1. Build `progress_callback` closure mapping `(label, current, total)` → `_set_progress(..., job=job)`
2. Call `run_pipeline(..., transcriber=transcriber, cancel_event=job["cancel"])`
3. On success: `job["result"] = srt_path`, call `_set_progress("done", ...)`
4. On `PipelineError` or cancellation: clean up job/SSE as today

### Integration Points
- `run_pipeline()` already imports `WhisperTranscriber` lazily — keep that pattern
- `threading.Event` cancellation: check `cancel_event.is_set()` after audio extraction, after transcription, after translation (before write_srt)
- If cancel is set mid-pipeline, raise `PipelineCancelledError` (new exception) or return a sentinel — consistent with how router currently calls `_cancel_job()`

</code_context>
