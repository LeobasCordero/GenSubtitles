# GenSubtitles — Project Roadmap

## Milestones

- ✅ **v1.0 MVP** — 40 phases, 82 plans (shipped 2026-04-22) — [archive](milestones/v1.0-ROADMAP.md)

## Phases

<details>
<summary>✅ v1.0 MVP (40 phases) — SHIPPED 2026-04-22</summary>

### Core Phases (1–13)

- [x] Phase 1: Project Infrastructure — 3/3 plans (completed 2026-04-02)
- [x] Phase 2: Audio Extraction Module — 3/3 plans (completed 2026-04-02)
- [x] Phase 3: Transcription Engine — 2/2 plans (completed 2026-04-02)
- [x] Phase 4: Translation Engine — 2/2 plans (completed 2026-04-03)
- [x] Phase 5: SRT Generation Module — 1/1 plan (completed 2026-04-03)
- [x] Phase 6: Core Pipeline Assembly — 2/2 plans (completed 2026-04-06)
- [x] Phase 7: CLI Interface — 2/2 plans (completed 2026-04-06)
- [x] Phase 8: FastAPI REST API Core — 3/3 plans (completed 2026-04-07)
- [x] Phase 9: FastAPI Extensions & Docs — 2/2 plans (completed 2026-04-07)
- [x] Phase 10: Documentation & E2E Validation — 3/3 plans (completed 2026-04-10)
- [x] Phase 11: Retroactive Verification — Core Modules — 2/2 plans (completed 2026-04-21)
- [x] Phase 12: Retroactive Verification + Pipeline Refactor — 3/3 plans (completed 2026-04-22)
- [x] Phase 13: Nyquist Compliance — All Phases — 2/2 plans (completed 2026-04-22)

### Backlog Phases (999.x)

- [x] Phase 999.1: GUI Interface — 2/2 plans
- [x] Phase 999.2: GUI — Clear Fields Button — 1/1 plan
- [x] Phase 999.3: GUI — Auto-populate Subtitle Path — 1/1 plan
- [x] Phase 999.4: GUI — Disable Fields During Pipeline — 1/1 plan
- [x] Phase 999.5: GUI — Elapsed Time Counter — 1/1 plan
- [x] Phase 999.9: GUI — Form Polish — 1/1 plan
- [x] Phase 999.10: Feature Expansion (Language, Formats, Settings, Help) — 6/6 plans
- [x] Phase 999.11: Subtitle Silence — VAD and Timestamp Quality — 2/2 plans
- [x] Phase 999.12: Translation Quality — Context-Aware and Engine Upgrade — 4/4 plans
- [x] Phase 999.13: Subtitle Style Settings — 2/2 plans
- [x] Phase 999.14: GUI — HTTP Timeout / SSE Async Job + Cancel — 3/3 plans
- [x] Phase 999.15: GUI — UI Bug Fixes and Polish — 1/1 plan
- [x] Phase 999.16: GUI — UI Language Setting — 1/1 plan
- [x] Phase 999.17: GUI — Installed Language Pairs Deduplication — 1/1 plan
- [x] Phase 999.18: Docs — README Update — 2/2 plans
- [x] Phase 999.19: Config — Configurable JSON Config File Location — 2/2 plans
- [x] Phase 999.20: Docs — CLI Tutorial — 2/2 plans
- [x] Phase 999.21: REFACTOR — Palette Colors Separation — 1/1 plan
- [x] Phase 999.22: REFACTOR — Separate GUI Styles from Components — 2/2 plans
- [x] Phase 999.23: REFACTOR — Apply SOLID Principles to GUI — 1/1 plan
- [x] Phase 999.24: REFACTOR — Localisation Separation — 1/1 plan
- [x] Phase 999.25: BUG — GUI s() TypeError — 0 plans (resolved as side effect of 999.24)
- [x] Phase 999.26: Console Log Display — 0 plans (resolved as part of 999.30)
- [x] Phase 999.27: Stepper Mode for Pipeline Steps — 5/5 plans
- [x] Phase 999.28: Stepper Work-Dir Auto-Subfolder — 2/2 plans
- [x] Phase 999.29: GUI — Rediseno Layout Tres Paneles — 3/3 plans
- [x] Phase 999.30: REFACTOR — GUI con Tabs por Funcionalidad — 4/4 plans

</details>

## Next Milestone

_No next milestone defined. Run /gsd-new-milestone to begin planning v1.1._

## Backlog

### Phase 999.31: BUG — GUI Transcription HTTP Timeout (BACKLOG)

**Goal:** Fix `HTTPConnectionPool(host='127.0.0.1', port=8000): Read timed out. (read timeout=600)` raised in the GUI when transcription exceeds the 600-second HTTP read timeout. Long videos (large files, slow models) fail silently from the GUI's perspective. Investigate whether the SSE async job pattern (Phase 999.14) fully covers this — the blocking `POST /subtitles` path may still be active in some code paths, or the SSE stream itself may be timing out.
**Requirements:** TBD
**Plans:** 1 plan

Plans:
- [ ] 999.31-01-PLAN.md — Fix `timeout=600` → `timeout=(5, None)` in `_run_step_in_bg`

---

### Phase 999.32: GUI — Mejoras UX, Paletas de Colores y Accesibilidad (COMPLETE)

**Goal:** Improve Tab 3-6 UX with smart filename auto-fill, universal button locking during operations, visual log separators, optional console-clear on field-clear, secondary button text contrast fix, a 6-palette color system with per-token customization, and i18n for all console log messages.
**Requirements:** D-01, D-02, D-03, D-04, D-05, D-06, D-07
**Plans:** 3/3 plans executed

Scope:
- Auto-populate filename placeholders (audio, subtitle, etc.) based on selected video filename (e.g. `video1.mkv` → `video1.wav`, `video1.srt`); user can override
- Disable action buttons (and buttons in other tabs) while a long-running process (transcription, extraction, etc.) is active
- Emit a visual separator in the console log at the start of each new process (e.g. a line of `---` or `***`)
- "Clear Fields" button also clears the console — only when the corresponding Settings toggle is enabled
- Fix secondary button font color to ensure sufficient contrast against the button background
- Color palette system: new Settings section with predefined palettes + user-customizable colors for primary buttons, secondary buttons, fonts, console background, tab backgrounds, dropdowns
- Translate console log messages according to the active UI language

Plans:
- [x] 999.32-01-PLAN.md — Foundation: theme.py palettes + styles.py contrast fix + settings.py new fields + locale.py all new keys
- [x] 999.32-02-PLAN.md — main.py Tab UX: filename chain (D-01), button locking (D-02), log separator (D-03), log i18n tabs 3-6 (D-07)
- [x] 999.32-03-PLAN.md — main.py Settings + Palette Panel: clear-console toggle (D-04), palette editor UI (D-06)

---

*Roadmap created: 2026-04-02*
*Last updated: 2026-04-29 — phase 999.32 complete (3/3 plans)*
