---
phase: 07-cli-interface
plan: "01"
status: complete
completed: "2026-04-06"
commit: 704ff24
---

# Plan 07-01 Summary: Implement Typer CLI

## What Was Built

Replaced the stub `gensubtitles/cli/main.py` with a full Typer CLI implementation exposing
`run_pipeline()` as a polished command with all 6 flags, progress output, auto-derived output
path, and correct exit codes.

## Key Files

### Modified
- `gensubtitles/cli/main.py` — Full Typer CLI replacing the 2-option stub (87 lines)

## Decisions Made

- `no_args_is_help=True` on the Typer app — plain `python main.py` shows help (satisfies CLI-02)
- `input` is `Path` type — Typer parses and resolves it; pipeline's `FileNotFoundError` surfaces a clean message
- Lazy import of `run_pipeline` inside `generate()` — keeps CLI importable without FFmpeg/GPU
- `except typer.Exit: raise` — prevents accidentally swallowing the success exit
- Auto-derived output: `input.with_suffix(".srt")` when `--output` omitted

## Verification

- `python -c "from gensubtitles.cli.main import app; print('import OK')"` → **import OK**
- All 6 flags present: `--input`, `--output`, `--model`, `--target-lang`, `--source-lang`, `--device`
- Progress callback emits `[N/4] label...` format
- `FileNotFoundError` → `Exit(code=1)`; any other exception → `Exit(code=1)`; success → `Exit(code=0)`

## Self-Check: PASSED
