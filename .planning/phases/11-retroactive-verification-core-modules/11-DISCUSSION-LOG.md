# Phase 11: Retroactive Verification — Core Modules - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-20
**Phase:** 11-retroactive-verification-core-modules
**Areas discussed:** Verification method, Evidence depth per requirement, VALIDATION.md handling, Partial/missing coverage

---

## Verification Method

| Option | Description | Selected |
|--------|-------------|----------|
| Run tests live, then write VERIFICATION.md based on current passing results | Confirms code still works today — most authoritative but requires test suite to be green | |
| Compile from existing UAT.md + summaries only (no test re-run) | Faster, all evidence already exists in .planning/ artifacts | ✓ |
| Run tests live AND cross-reference UAT.md artifacts for a dual-source record | Most thorough — test output + UAT notes both cited as evidence | |

**User's choice:** Compile from existing UAT.md + summaries only (no test re-run)
**Notes:** All evidence already exists in UAT.md files with pass/fail per test. No need to re-run.

---

## Evidence Depth Per Requirement

| Option | Description | Selected |
|--------|-------------|----------|
| File-level: cite test file name only | e.g. 'tests/test_audio.py' — same style used in Phase 10 VERIFICATION.md | ✓ |
| Function-level: cite specific test function + file | e.g. 'test_extract_audio_produces_wav (tests/test_audio.py)' — maps each requirement to specific test | |
| Full dual-source: test function + UAT.md result line | Both test functions and UAT.md result lines as dual evidence | |

**User's choice:** File-level: cite test file name only
**Notes:** Consistent with Phase 10's existing VERIFICATION.md style.

---

## VALIDATION.md Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Keep both alongside each other (different purpose) | Both files coexist — VALIDATION.md = execution sampling contract, VERIFICATION.md = formal exit record | |
| VERIFICATION.md supersedes VALIDATION.md (delete or archive old file) | VERIFICATION.md replaces or absorbs VALIDATION.md content (consolidates into one file) | ✓ |

**User's choice:** VERIFICATION.md supersedes VALIDATION.md
**Notes:** Phases 02 and 05 both have VALIDATION.md with `status: draft`. These will be deleted after VERIFICATION.md is created.

---

## Partial/Missing Coverage

| Option | Description | Selected |
|--------|-------------|----------|
| Mark as 'verified by inspection' with supporting evidence note | List it with status 'verified by inspection' and note what evidence supports it (e.g. code review / summary) | ✓ |
| Flag as coverage gap — defer formal verification to Phase 13 | Flag it in VERIFICATION.md as a gap, emit a note, and link to phase 13 (Nyquist) for coverage | |
| Mark VERIFICATION.md as partial/incomplete until coverage exists | Block the VERIFICATION.md with status: partial and add a TODO for what's missing | |

**User's choice:** Mark as 'verified by inspection' with supporting evidence note
**Notes:** Inspection evidence (code structure, summaries) is sufficient for this retroactive record. Not blocking.
