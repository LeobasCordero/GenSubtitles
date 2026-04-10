# Phase 9: FastAPI Extensions & API Documentation - Context

**Gathered:** 2026-04-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Complete the REST API surface: add `GET /languages` endpoint, `CORSMiddleware`, a `serve` CLI subcommand (Uvicorn), and confirm OpenAPI docs accessible at `/docs` and `/openapi.json`. No new pipeline logic — wiring only.

</domain>

<decisions>
## Implementation Decisions

### CORS Policy
- **D-01:** Use `allow_origins=["*"]` wildcard — no env var configuration needed for v1. This is a local/self-hosted tool; simplicity wins.

### `/languages` Empty-State Behavior
- **D-03:** `GET /languages` returns **HTTP 200** with `{"pairs": []}` when no Argos Translate models are installed. Returns **HTTP 200** with `{"pairs": [...]}` when models are present. (503 approach was considered but rejected — an empty list is a valid and informative response.)

### OpenAPI Docs Customization
- **D-04:** Add endpoint **tags** by constructing `APIRouter(tags=["subtitles"])` in `routers/subtitles.py`. Both `POST /subtitles` and `GET /languages` inherit the tag and appear grouped under `"subtitles"` in Swagger UI. The router is included via `app.include_router(subtitles_router)` without an extra `tags` override.

### the Agent's Discretion
- **D-02:** Whether `serve` exposes `--model-size`/`--device` flags or relies on env vars (`WHISPER_MODEL_SIZE`, `WHISPER_DEVICE`) is left to the planner. The lifespan already reads env vars; exposing flags that mutate env is unusual.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

No external specs — requirements fully captured in decisions above.

### Requirements
- `.planning/REQUIREMENTS.md` — API-05, API-06, API-07 are the three requirements this phase closes

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `gensubtitles/api/main.py` — `FastAPI` app already has `title`, `description`, `version`, `lifespan`, and exception handlers. Add `CORSMiddleware` and tags here.
- `gensubtitles/api/routers/subtitles.py` — `router = APIRouter()` with `POST /subtitles`. Add `GET /languages` to this same router.
- `gensubtitles/cli/main.py` — Typer `app` with `@app.callback` as `generate`. Add `serve` as a new `@app.command()`.
- `gensubtitles/core/translator.py` — `list_installed_pairs()` exists and returns `list[dict]`. Use it inside `GET /languages`.

### Established Patterns
- Sync `def` routes for CPU-bound work (Phase 8 decision — keep consistent)
- Lazy imports inside route bodies (e.g., `list_installed_pairs` import inside the endpoint body, not at module level — avoids Argos Translate import cost at startup)
- `uvicorn.run("gensubtitles.api.main:app", ...)` — import string form required when `reload=True` is used

### Integration Points
- `app.add_middleware(CORSMiddleware, ...)` goes in `api/main.py` after the `FastAPI()` instantiation
- `app.include_router(subtitles_router, tags=["subtitles"])` — add `tags` here to apply to all routes in router
- `serve` command in `cli/main.py` calls `uvicorn.run()` directly — Uvicorn is already in `requirements.txt`

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches for the `serve` command flags design.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 09-fastapi-extensions-api-documentation*
*Context gathered: 2026-04-07*
