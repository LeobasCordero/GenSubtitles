# Phase 1: Project Infrastructure - Research

**Researched:** 2026-04-02
**Domain:** Python project scaffolding — pyproject.toml, uv, package layout, Typer CLI stub
**Confidence:** HIGH (decisions locked in CONTEXT.md; stack verified in pre-phase SUMMARY.md)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** `requirements.txt` uses `>=` minimum versions (flexible, for developer installs)
- **D-02:** Lock file is managed by **uv** (`uv.lock`) — uv is the official toolchain for this project
- **D-03:** `requirements.txt` (flexible) is for development; `uv.lock` is for reproducible CI/production installs
- **D-04:** `pip install -r requirements.txt` remains documented as the pip-only fallback
- **D-05:** **uv** is the official toolchain — document `uv sync` as the primary install command
- **D-06:** `pyproject.toml` is authoritative for project metadata; `requirements.txt` is derived from it
- **D-07:** No Poetry, no pip-tools — uv handles virtual environment + lock file natively
- **D-08:** `requires-python = ">=3.11"` — accepts 3.11, 3.12, 3.13+ without modification
- **D-09:** FFmpeg availability check runs **at import time** of `gensubtitles/core/audio.py` (fail fast)
- **D-10:** Raise `EnvironmentError` (not a custom class) with a clear message directing the user to install FFmpeg
- **D-11:** Check via `shutil.which("ffmpeg")` — no subprocess spawn needed for the check itself
- **D-12:** Package layout:
  ```
  gensubtitles/
  ├── __init__.py
  ├── core/         (audio.py, transcriber.py, translator.py, srt_writer.py)
  ├── api/
  │   ├── main.py
  │   ├── dependencies.py
  │   └── routers/
  └── cli/
      └── main.py
  ```
- **D-13:** `api/dependencies.py` created as a stub in Phase 1 (filled in Phase 8)
- **D-14:** `main.py` at project root delegates to the CLI module (thin shim)
- **D-15:** `models/`, `temp/`, `output/` created at project root with `.gitkeep` placeholders and added to `.gitignore`

### Agent's Discretion

*(None specified — all decisions locked)*

### Deferred Ideas (OUT OF SCOPE)

*(None specified)*
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INF-01 | `requirements.txt` lists all dependencies with pinned versions | §Standard Stack table provides exact packages + `>=` versions; pyproject.toml is authoritative source |
| INF-02 | Project structure follows `core/` + `api/` + `cli/` separation | §Architecture Patterns documents exact layout from SUMMARY.md §6 and CONTEXT.md D-12 |
| INF-04 | FFmpeg as system dependency documented with install instructions per platform | §Common Pitfalls + §Code Examples document the shutil.which check; README section templates provided |
</phase_requirements>

---

## Summary

Phase 1 is pure scaffolding — no pipeline logic, no algorithms. All significant decisions are locked in CONTEXT.md from the `/gsd-discuss-phase` session, and the technical stack was already vetted in `.planning/research/SUMMARY.md`. Research here focuses on the mechanics of creating a correct `pyproject.toml` for uv, forming the `requirements.txt` from it, and writing minimal-but-correct Python stubs that downstream phases can fill in without changes.

Two environment gaps must be addressed in the execution plan: **uv is not installed** on this machine (uv is required per D-02/D-05), and **FFmpeg is not installed** (system dependency, documented in README per INF-04 — the Phase 1 code checks for it at import time but does not install it). The planner must include a uv installation step in Wave 0.

The entire phase is file-creation work. No external APIs, no model downloads, no network calls. Estimated execution: under 10 minutes of agent time.

**Primary recommendation:** Create pyproject.toml first (authoritative), derive requirements.txt from it, then scaffold all stub files. Commit at the end of each plan.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| faster-whisper | >=1.2.1 | Transcription engine (Phase 2+) | Already researched; listing here to pin in Phase 1 |
| argostranslate | >=1.11.0 | Offline translation (Phase 4+) | Already researched |
| srt | >=3.5.3 | SRT generation (Phase 5+) | Preferred over unmaintained pysrt |
| fastapi | >=0.135.3 | REST API framework (Phase 8+) | Industry standard async Python API |
| uvicorn[standard] | >=0.34.0 | ASGI server for FastAPI | Standard pairing; `[standard]` adds websockets support |
| python-multipart | >=0.0.20 | Required by FastAPI for file uploads | FastAPI raises 400 without it |
| typer[all] | >=0.15.0 | CLI framework (Phase 7+) | `[all]` adds `rich` (colored output) + `shellingham` (shell completion) |

> **Note:** `[standard]` and `[all]` extras are represented in `requirements.txt` as `uvicorn[standard]>=0.34.0` and `typer[all]>=0.15.0` respectively.

### Build / Dev Tooling

| Tool | Version | Purpose | Install |
|------|---------|---------|---------|
| uv | latest | Virtual env + lock file + project management | `pip install uv` or `winget install astral-sh.uv` |
| pytest | >=8.0.0 | Test framework (Wave 0 gap) | Listed in `[project.optional-dependencies.dev]` |

### FFmpeg (System Dependency — Not pip-installable)

FFmpeg must be installed separately per platform. It is documented in `requirements.txt` as a comment and in the README:
```
# SYSTEM DEPENDENCY: FFmpeg must be installed separately
# Linux:   sudo apt install ffmpeg
# macOS:   brew install ffmpeg
# Windows: winget install ffmpeg
```

**Versions for `requirements.txt`** (use `>=` per D-01):
```
faster-whisper>=1.2.1
argostranslate>=1.11.0
srt>=3.5.3
fastapi>=0.135.3
uvicorn[standard]>=0.34.0
python-multipart>=0.0.20
typer[all]>=0.15.0
```

---

## Architecture Patterns

### Recommended Project Structure (from CONTEXT.md D-12 + SUMMARY.md §6)

```
gensubtitles/
├── __init__.py                    # package version, __all__
├── core/
│   ├── __init__.py
│   ├── audio.py                   # FFmpeg check at import time + extraction stub
│   ├── transcriber.py             # faster-whisper stub
│   ├── translator.py              # argostranslate stub
│   └── srt_writer.py              # srt library stub
├── api/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app + lifespan stub
│   ├── dependencies.py            # model singleton stub (filled Phase 8)
│   └── routers/
│       ├── __init__.py
│       └── subtitles.py           # routes stub
└── cli/
    ├── __init__.py
    └── main.py                    # Typer app stub
main.py                            # thin shim → CLI
pyproject.toml                     # authoritative metadata + deps
requirements.txt                   # derived, >= pins, for pip fallback
uv.lock                            # generated by uv sync (gitignored? No — committed)
.gitignore
models/
├── .gitkeep
temp/
├── .gitkeep
output/
    └── .gitkeep
```

### Pattern 1: pyproject.toml for uv

`pyproject.toml` is the authoritative source (D-06). uv reads it to generate `uv.lock`.

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "gensubtitles"
version = "0.1.0"
description = "Automatic video subtitle generation — offline, no API keys required"
requires-python = ">=3.11"
dependencies = [
    "faster-whisper>=1.2.1",
    "argostranslate>=1.11.0",
    "srt>=3.5.3",
    "fastapi>=0.135.3",
    "uvicorn[standard]>=0.34.0",
    "python-multipart>=0.0.20",
    "typer[all]>=0.15.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
]

[project.scripts]
gensubtitles = "gensubtitles.cli.main:app"

[tool.hatch.build.targets.wheel]
packages = ["gensubtitles"]
```

> **Why hatchling?** uv uses hatchling as its default build backend and it requires zero configuration for a simple flat package layout like this one. Alternative: `setuptools` works too, but hatchling is cleaner.

### Pattern 2: requirements.txt (derived, pip fallback)

```
# Install: pip install -r requirements.txt
# Primary toolchain: uv sync (see pyproject.toml)
#
# SYSTEM DEPENDENCY: FFmpeg must be installed separately
# Linux:   sudo apt install ffmpeg
# macOS:   brew install ffmpeg
# Windows: winget install ffmpeg

faster-whisper>=1.2.1
argostranslate>=1.11.0
srt>=3.5.3
fastapi>=0.135.3
uvicorn[standard]>=0.34.0
python-multipart>=0.0.20
typer[all]>=0.15.0
```

### Pattern 3: FFmpeg Import-time Check (D-09, D-10, D-11)

Required content at the top of `gensubtitles/core/audio.py`:

```python
import shutil

if shutil.which("ffmpeg") is None:
    raise EnvironmentError(
        "FFmpeg is not installed or not on PATH. "
        "Install it with:\n"
        "  Linux:   sudo apt install ffmpeg\n"
        "  macOS:   brew install ffmpeg\n"
        "  Windows: winget install ffmpeg"
    )
```

This runs at import time — any module that imports `audio` will fail immediately with a clear message if FFmpeg is absent. No lazy check.

### Pattern 4: Root `main.py` shim (D-14)

```python
from gensubtitles.cli.main import app

if __name__ == "__main__":
    app()
```

This is intentionally minimal. `python main.py` invokes the Typer CLI. The module-level import means an `ImportError` here points directly at a broken package install, not ambiguous errors.

### Pattern 5: Minimal Typer stub for `gensubtitles/cli/main.py`

```python
import typer

app = typer.Typer(help="GenSubtitles — automatic subtitle generation.")


@app.command()
def generate(
    input: str = typer.Option(..., "--input", "-i", help="Path to input video file."),
    output: str = typer.Option("output/subtitles.srt", "--output", "-o", help="Output SRT path."),
) -> None:
    """Generate subtitles from a video file."""
    typer.echo("Not yet implemented — coming in a later phase.")
    raise typer.Exit(code=0)


if __name__ == "__main__":
    app()
```

This satisfies UAT: `python main.py` (or `python main.py --help`) prints usage without ImportError or AttributeError.

### Pattern 6: api/dependencies.py stub (D-13)

```python
"""
Model singleton and FastAPI Depends() injection.
Populated in Phase 8: FastAPI REST API Core.
"""
from __future__ import annotations

# Placeholder — filled in Phase 8
whisper_model = None
argos_model = None
```

### Anti-Patterns to Avoid

- **Don't import pipeline modules in `__init__.py`:** Top-level `gensubtitles/__init__.py` should only set `__version__`, not import `core` or `api`. Importing at package level triggers the FFmpeg check on `import gensubtitles`, which surprises users who only want the API.
- **Don't skip the `[build-system]` table in pyproject.toml:** uv requires it. Without it, `uv sync` may fall back to legacy behavior.
- **Don't check FFmpeg lazily:** The decision (D-09) is fail-fast at import time. Don't move the check inside the `extract_audio()` function — that delays the error until runtime.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CLI argument parsing | `argparse` or `sys.argv` | `typer[all]` | type-hint-based, auto-generates `--help`, shell completion |
| Lock file management | `pip freeze > requirements.txt` | `uv lock` / `uv.lock` | pip freeze captures transitive deps without intent; uv lock is reproducible and fast |
| pyproject.toml structure | Custom format | hatchling + standard `[project]` table | PEP 517/518 compliant; uv understands it natively |

**Key insight:** This phase is purely declarative. The plan should create files, not write algorithms. Any "logic" in Phase 1 stubs should be 1-3 lines.

---

## Common Pitfalls

### Pitfall 1: `uv` Not Installed
**What goes wrong:** `uv sync` fails with "command not found".
**Why it happens:** uv is not part of the Python standard toolchain; must be installed separately.
**How to avoid:** Wave 0 plan must include `pip install uv` (or `winget install astral-sh.uv`) as the first step. Verify with `uv --version`.
**Warning signs:** `uv : El término 'uv' no se reconoce...` — this was observed on this machine.

### Pitfall 2: `requirements.txt` Rewritten by uv
**What goes wrong:** `uv pip compile` overwrites the manually maintained `requirements.txt`.
**Why it happens:** uv's compile mode is designed to replace pip-tools workflows.
**How to avoid:** Don't use `uv pip compile` here. Maintain `requirements.txt` manually as the pip fallback. Let `uv.lock` be the machine-generated artifact.

### Pitfall 3: `api/routers/` missing `__init__.py`
**What goes wrong:** `from gensubtitles.api.routers import subtitles` raises `ModuleNotFoundError`.
**Why it happens:** Python requires `__init__.py` at every level for namespace packages resolution.
**How to avoid:** Create `__init__.py` in every directory: `gensubtitles/`, `core/`, `api/`, `api/routers/`, `cli/`.

### Pitfall 4: Root `__init__.py` importing `core`
**What goes wrong:** `import gensubtitles` triggers the FFmpeg check unexpectedly.
**Why it happens:** If `gensubtitles/__init__.py` does `from gensubtitles.core import audio`, importing the package triggers audio.py's import-time side effects.
**How to avoid:** Keep root `__init__.py` to only `__version__ = "0.1.0"` — nothing else.

### Pitfall 5: Hatchling not recognizing the package
**What goes wrong:** `uv sync` succeeds but `import gensubtitles` fails.
**Why it happens:** Without `[tool.hatch.build.targets.wheel] packages = ["gensubtitles"]`, hatchling may not find the package directory.
**How to avoid:** Always include the `packages` declaration in pyproject.toml.

---

## Code Examples

### Creating all `__init__.py` stubs

Root package:
```python
# gensubtitles/__init__.py
__version__ = "0.1.0"
```

Sub-packages (core, api, api/routers, cli):
```python
# gensubtitles/core/__init__.py  (and others)
# intentionally empty
```

### Minimal test to verify UAT criterion

```python
# tests/test_infrastructure.py
import os
import importlib

def test_package_directories_exist():
    for path in ["gensubtitles/core", "gensubtitles/api", "gensubtitles/cli"]:
        assert os.path.isdir(path), f"Missing directory: {path}"
        assert os.path.isfile(os.path.join(path, "__init__.py")), f"Missing __init__.py in {path}"

def test_cli_entrypoint_importable():
    """python main.py must not raise ImportError or AttributeError."""
    mod = importlib.import_module("gensubtitles.cli.main")
    assert hasattr(mod, "app"), "cli/main.py must expose 'app'"
```

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Everything | ✓ | 3.12.6 | — |
| pip | requirements.txt install | ✓ | 25.2 | — |
| uv | `uv sync`, lock file (D-02, D-05) | ✗ | — | `pip install uv` in Wave 0 |
| FFmpeg | `gensubtitles/core/audio.py` runtime | ✗ | — | System install (documented; not required for Phase 1 tests) |
| hatchling | Build backend for pyproject.toml | Unknown | — | Installed by uv automatically when running `uv sync` |

**Missing dependencies with no fallback:**
- None — uv can be installed via pip; FFmpeg is a system dep not required until Phase 2.

**Missing dependencies with fallback:**
- **uv:** Install via `pip install uv` as Wave 0 step. All uv commands then work as documented.
- **FFmpeg:** Not needed until Phase 2. Phase 1 creates the `audio.py` stub with the check but the check only fires on import, which is not triggered by Phase 1 tests.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest >=8.0.0 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` — Wave 0 gap |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INF-01 | requirements.txt has all packages with `>=` pins | unit | `pytest tests/test_infrastructure.py::test_requirements_pinned -x` | ❌ Wave 0 |
| INF-02 | `gensubtitles/core/`, `api/`, `cli/` all exist with `__init__.py` | unit | `pytest tests/test_infrastructure.py::test_package_directories_exist -x` | ❌ Wave 0 |
| INF-04 | FFmpeg absence raises EnvironmentError with install instructions | unit | `pytest tests/test_infrastructure.py::test_ffmpeg_check_raises -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_infrastructure.py -x -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/__init__.py` — make tests a package
- [ ] `tests/test_infrastructure.py` — covers INF-01, INF-02, INF-04
- [ ] pytest install: `uv add --dev pytest>=8.0.0` or add to `pyproject.toml [project.optional-dependencies].dev`
- [ ] `pyproject.toml` `[tool.pytest.ini_options]` section with `testpaths = ["tests"]`

---

## Sources

### Primary (HIGH confidence)
- `.planning/research/SUMMARY.md` §6 — project layout, confirmed against Phase 1 decisions
- `CONTEXT.md` — all implementation decisions (D-01 through D-15); authoritative for this phase
- Official uv docs: https://docs.astral.sh/uv/concepts/projects/ — pyproject.toml format, `uv sync`, lock file
- Typer docs: https://typer.tiangolo.com/ — `Typer()` instantiation, `@app.command()` pattern
- Hatchling docs: https://hatch.pypa.io/latest/config/build/ — `packages` declaration

### Secondary (MEDIUM confidence)
- Package versions from `.planning/research/SUMMARY.md` (verified against PyPI as of 2026-04-02 during the pre-phase research)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions sourced from pre-phase SUMMARY.md which was verified against PyPI/GitHub
- Architecture: HIGH — locked in CONTEXT.md, confirmed by SUMMARY.md §6
- Pitfalls: HIGH — uv absence is directly observed; others from SUMMARY.md §7

**Research date:** 2026-04-02
**Valid until:** 2026-07-02 (90 days — stable toolchain, not fast-moving)
