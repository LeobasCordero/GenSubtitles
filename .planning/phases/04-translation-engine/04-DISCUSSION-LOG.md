# Phase 4: Translation Engine - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-03  
**Phase:** 4 — Translation Engine  
**Branch:** phase-4-translation-engine (from origin/main)

---

## Areas Discussed

All four areas were selected by the user.

---

### Exception Design

**Q:** How should Phase 4 handle exceptions? The existing pattern adds a typed exception to exceptions.py per core module.

| Option | Description |
|--------|-------------|
| Add TranslationError(GenSubtitlesError) | Matches AudioExtractionError and TranscriptionError pattern |
| **Reuse built-in exceptions only** ✓ | ValueError for bad pairs; RuntimeError for network/install failures |
| TranslationError + ValueError hybrid | New exception + ValueError for unsupported pairs |

**Selected:** Reuse built-in exceptions only  
**Notes:** User explicitly chose not to follow the per-module custom exception pattern for this phase.

---

### Network Failure Behavior

**Q:** When `update_package_index()` fails (no internet): what should happen?

| Option | Description |
|--------|-------------|
| Warn and proceed when cached; fail if missing | Strict: only fail if pair is not installed |
| Raise RuntimeError on any network failure | Always fail on connectivity issues |
| **Best-effort: try network, fall back to cached** ✓ | Try network, log warning on failure, use whatever is available |

**Selected:** Best-effort: try network, fall back to cached  
**Follow-up:** If pair is cached after network failure → proceed silently. If pair is NOT cached after network failure → raise RuntimeError.

---

### Translated Segment Type

**Q:** What type should `translate_segments()` return for translated items?

| Option | Description |
|--------|-------------|
| namedtuple TranslatedSegment | Match existing TranscriptionResult pattern |
| @dataclass TranslatedSegment | Follow roadmap spec, more extensible |
| **No new type — dicts or original objects** ✓ | Minimal approach |

**Selected:** No new type  
**Follow-up Q:** When translation DOES happen, what format?

| Option |
|--------|
| Mutate/replace .text on existing objects |
| Return dicts |
| **You decide — agent picks cleanest approach** ✓ |

**Selected:** Agent discretion  
**Notes:** `.start`, `.end`, `.text` duck-typing must be preserved for Phase 5 SRT writer.

---

### Progress / Logging During Model Download

**Q:** How should model downloads be surfaced to the user?

| Option |
|--------|
| Python logging only |
| **Print to stdout** ✓ |
| Silent |

**Selected:** Print to stdout  

**Follow-up Q:** What level of stdout detail?

| Option |
|--------|
| Simple start + done messages |
| **Progress bar (tqdm)** ✓ |
| Single pre-download notice |

**Selected:** tqdm progress bar  
**Notes:** Planner must verify tqdm is in requirements.txt; add it if missing.
