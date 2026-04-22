# Phase 13: Nyquist Compliance — All Phases - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-22
**Phase:** 13-nyquist-compliance-all-phases
**Areas discussed:** VALIDATION.md vs VERIFICATION.md reconciliation, Content depth, Phase 05 treatment, Phase grouping for plans

---

## VALIDATION.md vs VERIFICATION.md Reconciliation

| Option | Description | Selected |
|--------|-------------|----------|
| A — Create new lightweight VALIDATION.md files | Retroactive attestation: frontmatter with nyquist_compliant: true + brief compliance summary linking to VERIFICATION.md | ✓ |
| B — Amend existing VERIFICATION.md frontmatter | Add nyquist fields directly to VERIFICATION.md, no new files | |
| C — Reconstruct full VALIDATION.md | Full task-map, wave 0 checklist, sampling rates — historically accurate but high effort | |

**User's choice:** A — Create new lightweight VALIDATION.md files
**Notes:** UAT criteria explicitly check for VALIDATION.md by name, so B was ruled out.

---

## Content Depth

| Option | Description | Selected |
|--------|-------------|----------|
| A1 — Frontmatter + evidence link only | Just YAML + 1-2 lines pointing to VERIFICATION.md | |
| A2 — Frontmatter + brief compliance summary | ~10-15 lines: test file, pass count, link to VERIFICATION.md | ✓ |
| A3 — Frontmatter + reconstructed key sections | Partial reconstruction of task-map + test infrastructure table | |

**User's choice:** A2 — Frontmatter + brief compliance summary
**Notes:** Retroactive context makes full reconstruction unnecessary; A2 provides enough traceability without busywork.

---

## Phase 05 Treatment

| Option | Description | Selected |
|--------|-------------|----------|
| Same as others | Create new 05-VALIDATION.md like all phases | ✓ |
| Skip phase 05 | Count VERIFICATION.md alone as sufficient; phase 05 is exception | |

**User's choice:** Same as others
**Notes:** Phase 05's VALIDATION.md was deleted in Phase 11. ROADMAP's "already compliant" note referred to a file that no longer exists.

---

## Phase Grouping for Plans

| Option | Description | Selected |
|--------|-------------|----------|
| Two plans | Phases 01–05 in plan 01, phases 06–10 in plan 02 | ✓ |
| One plan | All 10 phases in 2-3 tasks | |
| Five plans | One plan per 2 phases — maximum parallelism | |

**User's choice:** Two plans
**Notes:** Natural split at the v1.0 phase boundary (core modules vs API/CLI/docs). Both plans are independent and can execute in parallel (Wave 1).

---

## the agent's Discretion

- Exact wording of Compliance Summary prose
- Whether to label "Test file" vs "Tests" in the summary body

## Deferred Ideas

None.
