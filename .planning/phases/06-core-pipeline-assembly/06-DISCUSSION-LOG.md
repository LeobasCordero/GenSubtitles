# Phase 6: Core Pipeline Assembly - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-03  
**Phase:** 06-core-pipeline-assembly  
**Areas discussed:** Pre-loaded transcriber support, Progress callback when translation is skipped, `audio_duration_seconds` source

---

## Pre-loaded Transcriber Support

| Option | Description | Selected |
|--------|-------------|----------|
| `transcriber` parameter | Accept optional `WhisperTranscriber` instance; create internally when `None` | |
| `model_size` + `device` only | Always create fresh `WhisperTranscriber` inside `run_pipeline` | ✓ |
| You decide | Leave to planner — could use either or raw `WhisperModel` kwarg | |

**User's choice:** Option 2 — `model_size` + `device` only; Phase 8 handles model reuse at the API layer.  
**Notes:** Phase 8 `lifespan` preloads a model, but will wire that separately — `run_pipeline` stays simple and stateless.

---

## Progress Callback When Translation Is Skipped

| Option | Description | Selected |
|--------|-------------|----------|
| Always 4 calls, `total=4` | Emit `("Translating", 3, 4)` even when skipping | |
| 3 calls when skipping, `total=3` | Dynamic total based on whether translation runs | |
| 4 calls, skip named distinctly | Always `total=4`; emit `("Translation skipped", 3, 4)` when `target_lang=None` | ✓ |

**User's choice:** Option 3 — always 4 calls, use `"Translation skipped"` as stage name when no translation.  
**Notes:** Resolves the conflict between Phase 6 UAT ("exactly 4 times") and Phase 7 CLI UAT ("translation line may be skipped"). CLI can decide whether to display or suppress the skipped-translation line.

---

## `audio_duration_seconds` Source

| Option | Description | Selected |
|--------|-------------|----------|
| Read WAV via `wave` module | Post-extraction, compute `nframes / framerate` from temp WAV | |
| Extend `TranscriptionResult` with `duration` | Add `duration` field to namedtuple; `info.duration` already available in transcriber | ✓ |
| You decide | Leave to planner | |

**User's choice:** Option 2 — extend `TranscriptionResult`. Phase 6 plan updates `transcriber.py` and its 25-test suite.  
**Notes:** `faster_whisper` already returns `TranscriptionInfo.duration`; threading it through is minimal work with maximum correctness.

---

## Agent's Discretion

- `PipelineError` exception design (attribute shape vs message-only)
- `core/__init__.py` export decisions
- Input validation error message wording

## Deferred Ideas

None.
