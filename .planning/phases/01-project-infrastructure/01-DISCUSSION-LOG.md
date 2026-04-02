# Phase 1: Project Infrastructure - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-02  
**Phase:** 01-project-infrastructure  
**Areas discussed:** Pinning de dependencias, Toolchain de instalación, Validación de FFmpeg, Constraint de versión Python, API structure (from SUMMARY.md review)

---

## Pinning de dependencias

| Option | Description | Selected |
|--------|-------------|----------|
| == Exact pins | Reproducible, requires manual updates | |
| >= Minimums | Flexible, risk of silent breaking changes | |
| Dual: requirements + lock | requirements.txt (>=) + lock file (==) | ✓ |

**Follow-up: Lock file management**

| Option | Description | Selected |
|--------|-------------|----------|
| Mantener ambos manualmente | Dev and CI use separate files, manual sync | |
| pip-compile para el lock | pip-tools generates the lock from requirements.txt | ✓ (initial) |
| uv lock | uv manages the lock file natively | → superseded by Toolchain decision |

**Follow-up: Lock file role**

| Option | Description | Selected |
|--------|-------------|----------|
| Solo lock file | Lock replaces requirements.txt | |
| Dev vs prod split | requirements.txt for dev, lock for CI/prod | ✓ |

**User's choice:** Dual strategy — flexible requirements.txt + lock file for reproducibility. Lock management decision was later superseded by the uv decision (see Toolchain).

---

## Toolchain de instalación

| Option | Description | Selected |
|--------|-------------|----------|
| pip + venv estándar | Plain pip, universal but slow | |
| uv (recomendado) | 10-100x faster, requirements.txt compatible | ✓ |
| Poetry | opinionated, pyproject.toml-only | |

**Follow-up: uv integration depth**

| Option | Description | Selected |
|--------|-------------|----------|
| Solo documentación | uv mentioned in README only | |
| uv oficial con uv.lock | pyproject.toml + uv.lock, pip as fallback | ✓ |
| uv + pip-compile | uv for env, pip-compile for lock | |

**User's choice:** uv as official toolchain with `uv.lock`. This supersedes the earlier pip-compile decision — uv handles both virtual environment and lock file.

---

## Validación de FFmpeg

| Option | Description | Selected |
|--------|-------------|----------|
| Al importar (fail fast) | shutil.which at module import, EnvironmentError if absent | ✓ |
| Lazy (en el primer uso) | Check inside extract_audio() call | |
| Sin verificación | Let FFmpeg fail with its own error | |

**Follow-up: Error type**

| Option | Description | Selected |
|--------|-------------|----------|
| EnvironmentError | Standard Python exception | ✓ |
| Custom FFmpegNotFoundError | Inherits from EnvironmentError, more granular | |
| Warning only | Allows import without FFmpeg (useful for tests) | |

**User's choice:** `EnvironmentError` raised at import time of `gensubtitles/core/audio.py`.

---

## Constraint de versión Python

| Option | Description | Selected |
|--------|-------------|----------|
| >=3.11 flexible | Accepts 3.11, 3.12, 3.13+ | ✓ |
| >=3.11,<3.13 bounded | Capped at tested versions | |
| ==3.11.* estricto | Only Python 3.11.x | |

**User's choice:** `requires-python = ">=3.11"` in pyproject.toml.

---

## API Structure (from SUMMARY.md review)

The user reviewed `.planning/research/SUMMARY.md` §6 and identified the recommended split between `api/main.py` and `api/dependencies.py`.

| Option | Description | Selected |
|--------|-------------|----------|
| api/main.py + api/dependencies.py | research-recommended split, model singleton injected via Depends | ✓ |
| Solo api/main.py | Everything in one file, simpler | |

**User's choice:** Create both files as stubs in Phase 1, even though `dependencies.py` is filled in Phase 8.

---

## Agent's Discretion

- Exact dependency versions (which pinned version numbers to use in requirements.txt)
- README stub content beyond the documented headings
- .gitignore exact entries (beyond the documented list)
