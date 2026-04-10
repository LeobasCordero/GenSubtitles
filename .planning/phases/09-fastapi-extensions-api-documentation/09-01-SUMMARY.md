---
plan: "09-01"
phase: "09"
status: complete
completed: 2026-04-07
commit: c7fa2c2
requirements_satisfied:
  - API-05
  - API-07
---

# Plan 09-01: GET /languages Endpoint + CORS Middleware

## What Was Built

Added `GET /languages` route to the FastAPI router and registered `CORSMiddleware` on the application. Extended the test suite with 6 new tests verifying the endpoint, CORS headers, OpenAPI schema, and Swagger UI accessibility.

## Key Changes

### gensubtitles/api/routers/subtitles.py
- Added `@router.get("/languages")` endpoint returning `{"pairs": list_installed_pairs()}`
- Uses lazy import pattern (inside function body) consistent with existing router code

### gensubtitles/api/main.py
- Added `from fastapi.middleware.cors import CORSMiddleware` import
- Registered `CORSMiddleware` with `allow_origins=["*"]`, `allow_methods=["*"]`, `allow_headers=["*"]` immediately after `app = FastAPI(...)`

### tests/test_api.py
- Added `TestGetLanguages` class with 6 tests:
  - `test_get_languages_returns_200_with_pairs_key`
  - `test_get_languages_empty_when_no_models`
  - `test_get_languages_with_pairs`
  - `test_cors_header_present`
  - `test_openapi_json_includes_both_endpoints`
  - `test_docs_returns_200`
- All tests mock `list_installed_pairs` to avoid `argostranslate` dependency in test environment

## Verification

```
python -m pytest tests/test_api.py -v
```
Result: **15 passed** (9 existing + 6 new)

## Self-Check: PASSED

- [x] `GET /languages` returns HTTP 200 with `{"pairs": list}` JSON
- [x] `CORSMiddleware` registered with `allow_origins=["*"]`
- [x] `GET /docs` returns 200 (verified by TestClient)
- [x] `GET /openapi.json` contains `/languages` and `/subtitles` in paths
- [x] All tests in `tests/test_api.py` pass (15 total)
- [x] API-05 satisfied — language pairs endpoint implemented
- [x] API-07 satisfied — OpenAPI docs accessible and verified
