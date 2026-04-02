# Phase 1: Project Infrastructure - Context

**Gathered:** 2026-04-02  
**Status:** Ready for planning

<domain>
## Phase Boundary

Establish directory structure, pinned dependencies, build tooling, and scaffolding stubs so all subsequent phases can build on a clean, reproducible foundation. No pipeline logic is implemented here — this phase creates the empty skeleton.

</domain>

<decisions>
## Implementation Decisions

### Dependency Management
- **D-01:** `requirements.txt` uses `>=` minimum versions (flexible, for developer installs)
- **D-02:** Lock file is managed by **uv** (`uv.lock`) — uv is the official toolchain for this project
- **D-03:** `requirements.txt` (flexible) is for development; `uv.lock` is for reproducible CI/production installs
- **D-04:** `pip install -r requirements.txt` remains documented as the pip-only fallback

### Build Tooling
- **D-05:** **uv** is the official toolchain — document `uv sync` as the primary install command
- **D-06:** `pyproject.toml` is authoritative for project metadata; `requirements.txt` is derived from it
- **D-07:** No Poetry, no pip-tools — uv handles virtual environment + lock file natively

### Python Version
- **D-08:** `requires-python = ">=3.11"` — accepts 3.11, 3.12, 3.13+ without modification

### FFmpeg Validation
- **D-09:** FFmpeg availability check runs **at import time** of `gensubtitles/core/audio.py` (fail fast, not lazy)
- **D-10:** Raise `EnvironmentError` (not a custom class) with a clear message directing the user to install FFmpeg
- **D-11:** Check via `shutil.which("ffmpeg")` — no subprocess spawn needed for the check itself

### Package Structure
- **D-12:** Package layout follows the research recommendation exactly:
  ```
  gensubtitles/
  ├── __init__.py
  ├── core/         (audio.py, transcriber.py, translator.py, srt_writer.py)
  ├── api/
  │   ├── main.py          (FastAPI app + lifespan)
  │   ├── dependencies.py  (model singleton + Depends — stub in Phase 1, filled in Phase 8)
  │   └── routers/         (subtitle routes)
  └── cli/
      └── main.py
  ```
- **D-13:** `api/dependencies.py` is created as a stub in Phase 1 (even though it's filled in Phase 8) — this establishes the module location early
- **D-14:** `main.py` at project root delegates to the CLI module (thin shim)

### Gitignored Directories
- **D-15:** `models/`, `temp/`, `output/` created at project root with `.gitkeep` placeholders and added to `.gitignore`

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — INF-01, INF-02, INF-04 (the requirements this phase satisfies)

### Research Findings
- `.planning/research/SUMMARY.md` §6 "Project Structure: Python CLI + API Hybrid" — recommended layout, key conventions, model loading pattern

### Roadmap
- `.planning/ROADMAP.md` Phase 1 plans and UAT criteria

No external specs beyond the above research — all decisions captured in `<decisions>` above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `main.py` — exists as a skeleton; Phase 1 replaces its body with a CLI shim
- `README.md` — exists; Phase 1 overwrites with the documented stub
- `requirements.txt` — exists but empty; Phase 1 populates it

### Established Patterns
- No patterns yet — this phase establishes them

### Integration Points
- All subsequent phases import from `gensubtitles/core/`, `gensubtitles/api/`, or `gensubtitles/cli/`
- `main.py` is the user-facing entry point for both CLI and API

</code_context>

<specifics>
## Specific Ideas

- User reviewed `.planning/research/SUMMARY.md` during discussion and confirmed the recommended project layout
- uv selection is deliberate — prefer modern tooling, not legacy pip-only workflow
- `api/dependencies.py` stub should be created in Phase 1 even though it's filled in Phase 8 — avoids import errors in early phases

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-project-infrastructure*  
*Context gathered: 2026-04-02*
