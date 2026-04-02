---
phase: 1
slug: project-infrastructure
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-02
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=8.0.0 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` — Wave 0 installs |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_infrastructure.py -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | INF-02 | unit | `pytest tests/test_infrastructure.py::test_package_directories_exist -x` | ❌ W0 | ⬜ pending |
| 1-02-01 | 01 | 1 | INF-01 | unit | `pytest tests/test_infrastructure.py::test_requirements_pinned -x` | ❌ W0 | ⬜ pending |
| 1-03-01 | 01 | 1 | INF-01 | unit | `pytest tests/test_infrastructure.py::test_pyproject_metadata -x` | ❌ W0 | ⬜ pending |
| 1-04-01 | 01 | 1 | INF-04 | unit | `pytest tests/test_infrastructure.py::test_ffmpeg_check_raises -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/__init__.py` — make tests a package
- [ ] `tests/test_infrastructure.py` — stubs covering INF-01, INF-02, INF-04
- [ ] pytest install: add `pytest>=8.0.0` to `pyproject.toml` `[project.optional-dependencies].dev`
- [ ] `pyproject.toml` `[tool.pytest.ini_options]` section with `testpaths = ["tests"]`

*Existing infrastructure covers all phase requirements via Wave 0 stubs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `pip install -r requirements.txt` installs without conflicts | INF-01 | Requires live network + full Python env | Run `pip install -r requirements.txt` in a fresh venv; confirm exit code 0 |
| FFmpeg install note visible in README | INF-04 | Documentation review | Open README.md; confirm `## Installation` section contains platform-specific FFmpeg notes for apt/brew/winget |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
