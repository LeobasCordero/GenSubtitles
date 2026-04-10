# Phase 9: FastAPI Extensions & API Documentation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-07
**Phase:** 09 — FastAPI Extensions & API Documentation

---

## Area A: CORS Policy

**Question:** How should CORS origins be configured?

**Options presented:**
1. `allow_origins=["*"]` — Wildcard, allows all origins. Simplest approach for a local/self-hosted tool.
2. Env var `CORS_ORIGINS` — Defaults to `["*"]` but overridable. Slightly more flexible.
3. No CORS middleware — Skip it; not required by API-05/06/07.

**User selected:** Option 1 — `allow_origins=["*"]`

**Decision captured:** D-01

---

## Area B: `serve` Command — Model Control

**Question:** Should `python main.py serve` expose `--model-size`/`--device` flags, or rely on env vars?

**Options presented:**
1. Env vars only (`WHISPER_MODEL_SIZE`, `WHISPER_DEVICE`) — `serve` only takes `--host`, `--port`, `--reload`.
2. Expose `--model-size` / `--device` flags — Maps to env vars internally.
3. Agent's discretion — Leave it to the planner.

**User selected:** Option 3 — Agent's discretion

**Decision captured:** D-02

---

## Area C: `/languages` Empty-State Behavior

**Question:** What should `GET /languages` return when no Argos models are installed?

**Options presented:**
1. `{"pairs": []}` with HTTP 200 — Always succeeds, empty list signals "none installed."
2. HTTP 503 with `{"detail": "No language models installed"}` — Signals service not ready.
3. HTTP 200 with a `message` field — Informative but adds undocumented fields.

**User selected:** Option 2 — HTTP 503 when no models installed

**Decision captured:** D-03

---

## Area D: OpenAPI Docs Customization

**Question:** How much should the OpenAPI docs be dressed up?

**Options presented:**
1. Auto-gen as-is — No extra work, docstrings appear in Swagger UI.
2. Add response examples — Explicit example payloads for both endpoints.
3. Add endpoint tags — Group endpoints under a `"subtitles"` tag in Swagger UI.

**User selected:** Option 3 — Add endpoint tags

**Decision captured:** D-04
