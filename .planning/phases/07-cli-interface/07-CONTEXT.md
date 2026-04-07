# Phase 7: CLI Interface - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Expose `run_pipeline()` as a polished command-line tool via `gensubtitles/cli/main.py`. Delivers 6 Typer flags, Rich progress bar, Rich error panel, auto-derived output path, and correct exit codes. No API endpoints, no model caching, no new core modules — those belong to Phases 8+.

</domain>

<decisions>
## Implementation Decisions

### Progress Display
- **D-01:** Print plain `[N/4] <stage>...` lines via `typer.echo` for each pipeline stage. One line per stage, no Rich progress bar.
- **D-02:** No additional Rich dependency required — `typer.echo` is sufficient for the chosen output style.

### Output Path
- **D-03:** When `--output` is omitted, derive the output path as **same directory as input, same stem, `.srt` extension**. Example: `path/to/video.mp4` → `path/to/video.srt`. Do NOT use `output/` subdirectory or CWD.

### Error Messaging
- **D-04:** On any exception, print a plain `Error: <message>` line via `typer.echo(..., err=True)`. No Python traceback shown to the user. Exit code 1 for all pipeline errors, FileNotFoundError, etc.

### Flag Validation
- **D-05:** CLI validates **`--input` file existence only** before calling `run_pipeline()`. If the path does not exist, print a plain error message and exit 1 immediately. Model size, device, and language validation are delegated to the pipeline (they already raise appropriate errors).

### Agent's Discretion
- Default `--model` value — `"small"` is the existing pipeline default; planner should keep it consistent.
- Default `--device` value — `"auto"` is the existing pipeline default.
- Whether to print a success summary line after completion (e.g., `Saved: path/to/video.srt, 42 segments`) — planner decides.
- `--source-lang` default — `None` (auto-detect); consistent with pipeline.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — CLI-01, CLI-02, CLI-03, CLI-04

### Roadmap
- `.planning/ROADMAP.md` — Phase 7 goal, plans, and UAT criteria

### Prior Phase Contexts
- `.planning/phases/06-core-pipeline-assembly/06-CONTEXT.md` — D-02 progress callback contract (4 stages, always fires, "Translation skipped" when target_lang=None); D-01 run_pipeline signature

No external specs — requirements fully captured in decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `gensubtitles/cli/main.py` — existing stub with `--input` and `--output` only; to be replaced entirely
- `gensubtitles/core/pipeline.py` — `run_pipeline()` with `progress_callback: Callable[[str, int, int], None]` parameter; `PipelineResult` dataclass
- `gensubtitles/exceptions.py` — `PipelineError`, `GenSubtitlesError` (catch these for clean error display)
- `typer[all]>=0.15.0` — already installed, includes `rich`

### Established Patterns
- `from __future__ import annotations` at top of every module
- `pathlib.Path` used throughout for file operations
- `gensubtitles/__init__.py` has only `__version__` — no core imports
- Root `main.py` is a thin shim delegating to `gensubtitles.cli.main app`

### Integration Points
- `run_pipeline()` progress_callback signature: `(stage_name: str, current: int, total: int) -> None`
- CLI calls `run_pipeline(video_path, output_path, model_size, target_lang, source_lang, device, progress_callback)`
- Progress bar must be created before calling `run_pipeline()` and updated inside the callback

</code_context>

<specifics>
## Specific Ideas

- Plain `[N/4] <stage>...` lines via `typer.echo` for progress output
- Plain `Error: <message>` line via `typer.echo(..., err=True)` on failure (no traceback)
- Output path derivation: `Path(input).with_suffix(".srt")` — same dir, same stem

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 07-cli-interface*
*Context gathered: 2026-04-06*
