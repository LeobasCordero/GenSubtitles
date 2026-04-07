---
plan: "09-02"
phase: "09"
status: complete
completed: 2026-04-07
commit: 3cb8c5b
requirements_satisfied:
  - API-06
---

# Plan 09-02: CLI `serve` Subcommand

## What Was Built

Added `serve` Typer subcommand to `gensubtitles/cli/main.py` that launches the FastAPI app via `uvicorn.run()`. Made a minimal, necessary modification to the `generate` callback to support subcommand routing (added `ctx: typer.Context` parameter + subcommand guard). Added 3 tests verifying default invocation, custom args, and help output.

## Key Changes

### gensubtitles/cli/main.py
- Modified `generate` callback signature to include `ctx: typer.Context` as first parameter
- Made `--input`/`video_path` optional (default `None`) to prevent Typer from blocking subcommand routing
- Added subcommand guard: `if ctx.invoked_subcommand is not None: return`
- Added manual `None` check for `video_path` (preserves required-field semantics)
- Added `@app.command("serve")` function wrapping `uvicorn.run("gensubtitles.api.main:app", ...)`
- Uses lazy import for `uvicorn` (inside function body) consistent with the existing lazy import pattern

### tests/test_cli.py
- Added `TestServeCommand` class with 3 tests:
  - `test_serve_invokes_uvicorn_with_defaults` — mocks uvicorn via sys.modules injection (uvicorn not installed in test env)
  - `test_serve_accepts_custom_host_port`
  - `test_serve_help_shows_options`

## Design Note

The `generate` callback modification was necessary because Typer/Click group callbacks with required options prevent subcommands from being invoked. The `ctx.invoked_subcommand` guard preserves all existing generate functionality while enabling the serve subcommand. All 8 existing CLI tests continue to pass.

## Verification

```
python -m pytest tests/test_cli.py -v
```
Result: **11 passed** (8 existing + 3 new)

Spot-check:
```
python -c "from gensubtitles.cli.main import app; cmds=[c.name for c in app.registered_commands]; assert 'serve' in cmds"
```

## Self-Check: PASSED

- [x] `serve` Typer subcommand registered in `gensubtitles/cli/main.py`
- [x] `uvicorn.run()` called with import string `"gensubtitles.api.main:app"`
- [x] `--host`, `--port`, `--reload` options with documented defaults
- [x] All 11 tests in `tests/test_cli.py` pass (8 existing + 3 new)
- [x] `python main.py --input ...` (existing generate) unaffected
- [x] API-06 satisfied
