# Phase 10: Documentation & End-to-End Validation - Context

**Gathered:** 2026-04-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Write complete user-facing documentation in README.md (English) and README.es.md (Spanish), covering installation, CLI usage, API usage, language model behavior, and troubleshooting. Validate the full pipeline end-to-end with both CLI and API paths using a synthetic test video.

Satisfies: **INF-03** — README documents installation, CLI usage, and API usage with examples.

</domain>

<decisions>
## Implementation Decisions

### README Structure & Depth
- **D-01:** Practical guide level — Installation, CLI usage with all flags, API usage with all endpoints, language model download notes. ~200 lines per language.
- **D-02:** No model size tradeoff table — just mention model sizes are configurable via `--model` flag with a pointer to faster-whisper docs.
- **D-03:** Document Argos Translate download behavior — first use downloads, cached locally, offline after first run.

### Code Examples
- **D-04:** Bash + curl only (no Python snippets for API examples).
- **D-05:** 4 focused examples — 1 basic CLI, 1 CLI with translation, 1 API POST /subtitles, 1 API GET /languages.
- **D-06:** Bilingual as **two separate files** — `README.md` (English) + `README.es.md` (Spanish). Spanish file is a full translation, not a subset.

### Troubleshooting
- **D-07:** Cover exactly 3 failure modes: FFmpeg not found, Argos model download failures, missing output directory.
- **D-08:** No GPU/CUDA section — skip GPU-specific documentation. Just mention `--device` flag exists.

### E2E Validation
- **D-09:** Validate both CLI and API paths end-to-end with real transcription.
- **D-10:** Test with and without translation (one CLI run without `--target-lang`, one with).
- **D-11:** Generate a synthetic test video with FFmpeg (short clip with spoken audio via TTS or similar) rather than relying on external files.

### Agent's Discretion
- README section ordering and formatting
- Exact wording of troubleshooting solutions
- Synthetic video generation approach (FFmpeg lavfi, TTS, etc.)
- Whether to add a language switcher link between README.md and README.es.md

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing Documentation
- `README.md` — Current skeletal README to be replaced
- `.planning/REQUIREMENTS.md` — INF-03 requirement and all API/CLI requirements

### CLI Implementation
- `gensubtitles/cli/main.py` — All CLI flags, help text, and usage patterns
- `main.py` — Root entry point shim

### API Implementation
- `gensubtitles/api/main.py` — FastAPI app, lifespan, serve command
- `gensubtitles/api/routers/subtitles.py` — POST /subtitles and GET /languages endpoints

### Core Modules
- `gensubtitles/core/transcriber.py` — VALID_MODEL_SIZES, WhisperTranscriber
- `gensubtitles/core/translator.py` — translate_segments, language pair functions
- `gensubtitles/core/audio.py` — SUPPORTED_EXTENSIONS, FFmpeg requirement

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `README.md` exists with skeletal structure (Installation with FFmpeg + pip, basic CLI usage, placeholder API section)
- CLI help text in `gensubtitles/cli/main.py` documents all 6 flags with descriptions
- API docstrings in `gensubtitles/api/main.py` show serve command

### Established Patterns
- CLI entry: `python main.py --input video.mp4 [flags]`
- API serve: `python main.py serve` or `uvicorn gensubtitles.api.main:app`
- API endpoints: `POST /subtitles` (file upload), `GET /languages` (JSON pairs)
- CORS enabled with `allow_origins=["*"]`

### Integration Points
- README replaces existing `README.md` at project root
- README.es.md is a new file at project root
- E2E validation produces output in `output/` or `temp/` directories

</code_context>

<specifics>
## Specific Ideas

- Spanish README should be a complete standalone translation, not abbreviated
- Curl examples should be copy-pasteable
- Troubleshooting section anchored to the 3 most common failure modes from UAT experience

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 10-documentation-end-to-end-validation*
*Context gathered: 2026-04-10*
