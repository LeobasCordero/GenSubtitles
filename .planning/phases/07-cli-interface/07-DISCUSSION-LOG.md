# Phase 7: CLI Interface - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Session date:** 2026-04-06
**Phase:** 07-cli-interface

---

## Context Check

Phase 7 had 2 existing plans (07-01, 07-02) created without user context. User chose to continue and replan after discussion.

---

## Area 1: Progress Display Style

**Question:** How should the 4 progress lines look and feel?

| Option | Description |
|--------|-------------|
| Plain `typer.echo` | `[1/4] Extracting audio...` to stdout, no color |
| **Rich progress bar** ✓ | Animated bar with stage name as description |
| Plain echo with color | `typer.style()` coloring, no extra deps |

**Selected:** Rich progress bar

**Follow-up — Rich style:**

| Option | Description |
|--------|-------------|
| Spinner per stage | Each `[N/4]` line shows spinner while running, ✓ when done |
| **Single progress bar** ✓ | One bar advancing 25% per stage, stage name as description |
| Status panel | `rich.status` single overwriting line |

**Selected:** Single progress bar

**Note:** `rich` already available via `typer[all]>=0.15.0` — no new dependency.

---

## Area 2: Output Path Behavior

**Question:** When `--output` is omitted, where should the SRT be saved?

| Option | Example |
|--------|---------|
| **Same dir as input, same stem** ✓ | `path/to/video.mp4` → `path/to/video.srt` |
| CWD, same stem | `video.mp4` → `./video.srt` |
| `output/` subdirectory | `video.mp4` → `output/video.srt` |

**Selected:** Same directory as input, same stem.

---

## Area 3: Error Messaging

**Question:** What should the user see when something goes wrong?

| Option | Description |
|--------|-------------|
| Clean message to stderr | `Error: File not found: video.mp4`, no traceback, exit 1 |
| **Rich error panel** ✓ | Styled error box, consistent with progress bar |
| Typer default | Exception + traceback on unhandled errors |

**Selected:** Rich error panel — visually consistent with progress bar choice.

---

## Area 4: Flag Defaults & Validation

**Question:** What additional validation beyond Typer's built-in checks?

| Option | Description |
|--------|-------------|
| Minimal validation | Only Typer's free checks, trust pipeline |
| Eager validation | Validate `--input`, `--model`, `--device` at CLI level |
| **Middle ground** ✓ | Validate `--input` existence only at CLI level |

**Selected:** Middle ground — `--input` existence checked by CLI, model/device/lang delegated to pipeline.

---

## Summary of Decisions

| ID | Decision |
|----|----------|
| D-01 | Single Rich progress bar, 25% per stage, stage name as description |
| D-02 | `rich` available via `typer[all]` — no new dep |
| D-03 | Default output = same dir as input, same stem, `.srt` extension |
| D-04 | Rich error panel on failure, no traceback, exit 1 |
| D-05 | CLI validates `--input` existence only; rest delegated to pipeline |
