"""
Phase 1 infrastructure tests — covers INF-01, INF-02, INF-04.
"""
import os
import subprocess
import sys


def test_package_directories_exist():
    """INF-02: core/ + api/ + cli/ separation exists with __init__.py at every level."""
    required = [
        "gensubtitles/__init__.py",
        "gensubtitles/core/__init__.py",
        "gensubtitles/api/__init__.py",
        "gensubtitles/api/routers/__init__.py",
        "gensubtitles/cli/__init__.py",
    ]
    for path in required:
        assert os.path.exists(path), f"Missing: {path}"


def test_requirements_pinned():
    """INF-01: requirements.txt lists all deps with >= pins; no bare package names."""
    with open("requirements.txt") as f:
        lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]

    expected_packages = [
        "faster-whisper",
        "argostranslate",
        "srt",
        "fastapi",
        "uvicorn",
        "python-multipart",
        "typer",
    ]
    content = "\n".join(lines)
    for pkg in expected_packages:
        assert pkg in content, f"Missing package in requirements.txt: {pkg}"

    for line in lines:
        assert ">=" in line or "==" in line, (
            f"Line '{line}' has no version pin (>= or ==)"
        )


def test_pyproject_metadata():
    """INF-01: pyproject.toml has project metadata, requires-python, and all deps."""
    import tomllib

    with open("pyproject.toml", "rb") as f:
        data = tomllib.load(f)

    project = data["project"]
    assert project["name"] == "gensubtitles"
    assert project["requires-python"] == ">=3.11"
    assert "faster-whisper>=1.2.1" in project["dependencies"]
    assert "typer[all]>=0.15.0" in project["dependencies"]
    assert "gensubtitles" in data.get("project", {}).get("scripts", {}).get(
        "gensubtitles", ""
    )


def test_ffmpeg_check_raises():
    """INF-04: gensubtitles/core/audio.py raises EnvironmentError at import time if FFmpeg absent."""
    # Run import in a subprocess with PATH emptied so ffmpeg is definitely absent
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import os; os.environ['PATH'] = ''; import gensubtitles.core.audio",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0, "Expected non-zero exit when FFmpeg absent"
    assert "EnvironmentError" in result.stderr or "FFmpeg" in result.stderr, (
        f"Expected EnvironmentError mention in stderr, got: {result.stderr}"
    )
