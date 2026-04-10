"""Phase 7 CLI tests — covers CLI-01 through CLI-04."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from gensubtitles.cli.main import app

runner = CliRunner()


@dataclass
class _FakePipelineResult:
    srt_path: str
    detected_language: str
    segment_count: int
    audio_duration_seconds: float


def _make_result(srt_path: str = "out.srt") -> _FakePipelineResult:
    return _FakePipelineResult(
        srt_path=srt_path,
        detected_language="en",
        segment_count=3,
        audio_duration_seconds=30.0,
    )


def test_success_exits_zero(tmp_path):
    """CLI-04: exit code is 0 on success."""
    video = tmp_path / "video.mp4"
    video.touch()
    output = tmp_path / "out.srt"
    with patch(
        "gensubtitles.core.pipeline.run_pipeline",
        return_value=_make_result(str(output)),
    ):
        result = runner.invoke(app, ["--input", str(video), "--output", str(output)])
    assert result.exit_code == 0


def test_progress_lines_printed(tmp_path):
    """CLI-03: [1/4]...[4/4] appear on stdout."""
    video = tmp_path / "video.mp4"
    video.touch()
    output = tmp_path / "out.srt"

    def fake_pipeline(*args, progress_callback=None, **kwargs):
        if progress_callback:
            progress_callback("Extracting audio", 1, 4)
            progress_callback("Transcribing", 2, 4)
            progress_callback("Translation skipped", 3, 4)
            progress_callback("Writing SRT", 4, 4)
        return _make_result(str(output))

    with patch("gensubtitles.core.pipeline.run_pipeline", side_effect=fake_pipeline):
        result = runner.invoke(app, ["--input", str(video), "--output", str(output)])
    assert "[1/4] Extracting audio..." in result.stdout
    assert "[4/4] Writing SRT..." in result.stdout
    assert result.exit_code == 0


def test_help_lists_all_flags():
    """CLI-02: --help output lists all 6 option names."""
    import re

    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    output = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout)
    for flag in ["--input", "--output", "--model", "--target-lang", "--source-lang", "--device"]:
        assert flag in output, f"Missing flag in --help: {flag}"


def test_auto_derives_output_from_input(tmp_path):
    """CLI-01: When --output omitted, output path is derived from input stem as .srt."""
    video = tmp_path / "myvideo.mp4"
    video.touch()
    with patch(
        "gensubtitles.core.pipeline.run_pipeline",
        return_value=_make_result(str(tmp_path / "myvideo.srt")),
    ) as mock_run:
        result = runner.invoke(app, ["--input", str(video)])
    assert result.exit_code == 0
    _args, kwargs = mock_run.call_args
    call_output = kwargs.get("output_path") or (_args[1] if len(_args) > 1 else None)
    assert Path(str(call_output)).suffix == ".srt"
    assert "myvideo" in str(call_output)


def test_missing_input_exits_nonzero():
    """CLI-04: Missing --input flag → non-zero exit, usage error."""
    result = runner.invoke(app, ["--output", "out.srt"])
    assert result.exit_code != 0


def test_nonexistent_file_exits_one(tmp_path):
    """CLI-04: Non-existent input file → exit 1, error message names the file."""
    missing = tmp_path / "nonexistent.mp4"
    output = tmp_path / "out.srt"
    result = runner.invoke(app, ["--input", str(missing), "--output", str(output)])
    assert result.exit_code == 1
    assert "nonexistent" in result.stderr


def test_all_flags_forwarded(tmp_path):
    """CLI-01: All 6 CLI options are forwarded to run_pipeline()."""
    video = tmp_path / "video.mp4"
    video.touch()
    output = tmp_path / "out.srt"
    with patch(
        "gensubtitles.core.pipeline.run_pipeline",
        return_value=_make_result(str(output)),
    ) as mock_run:
        runner.invoke(
            app,
            [
                "--input", str(video),
                "--output", str(output),
                "--model", "tiny",
                "--target-lang", "es",
                "--source-lang", "en",
                "--device", "cpu",
            ],
        )
    _args, kwargs = mock_run.call_args
    assert kwargs.get("model_size") == "tiny"
    assert kwargs.get("target_lang") == "es"
    assert kwargs.get("source_lang") == "en"
    assert kwargs.get("device") == "cpu"


def test_pipeline_error_exits_one(tmp_path):
    """CLI-04: Any pipeline exception → exit 1, error printed to output."""
    from gensubtitles.exceptions import PipelineError

    video = tmp_path / "video.mp4"
    video.touch()
    output = tmp_path / "out.srt"
    with patch(
        "gensubtitles.core.pipeline.run_pipeline",
        side_effect=PipelineError("[transcription] boom"),
    ):
        result = runner.invoke(app, ["--input", str(video), "--output", str(output)])
    assert result.exit_code == 1
    assert "boom" in result.stderr


class TestServeCommand:
    """Phase 9 — covers API-06 (CLI serve subcommand)."""

    def _mock_uvicorn(self):
        """Inject a fake uvicorn module so tests work without uvicorn installed."""
        import sys
        from types import ModuleType
        from unittest.mock import MagicMock

        mock_uvicorn = ModuleType("uvicorn")
        mock_uvicorn.run = MagicMock()  # type: ignore[attr-defined]
        self._prev_uvicorn = sys.modules.get("uvicorn")
        sys.modules["uvicorn"] = mock_uvicorn
        return mock_uvicorn

    def _restore_uvicorn(self):
        """Restore the previously saved uvicorn entry in sys.modules."""
        import sys

        if self._prev_uvicorn is None:
            sys.modules.pop("uvicorn", None)
        else:
            sys.modules["uvicorn"] = self._prev_uvicorn

    def test_serve_invokes_uvicorn_with_defaults(self):
        """serve subcommand calls uvicorn.run with default host, port, and reload=False."""
        import sys

        mock_uvicorn = self._mock_uvicorn()
        try:
            result = runner.invoke(app, ["serve"])
        finally:
            self._restore_uvicorn()
        assert result.exit_code == 0
        mock_uvicorn.run.assert_called_once_with(
            "gensubtitles.api.main:app",
            host="127.0.0.1",
            port=8000,
            reload=False,
        )

    def test_serve_accepts_custom_host_port(self):
        """serve --host and --port are forwarded to uvicorn.run."""
        import sys

        mock_uvicorn = self._mock_uvicorn()
        try:
            result = runner.invoke(app, ["serve", "--host", "127.0.0.1", "--port", "9000"])
        finally:
            self._restore_uvicorn()
        assert result.exit_code == 0
        _, kw = mock_uvicorn.run.call_args
        assert kw.get("host") == "127.0.0.1"
        assert kw.get("port") == 9000

    def test_serve_help_shows_options(self):
        """serve --help output lists --host, --port, and --reload options."""
        result = runner.invoke(app, ["serve", "--help"])
        assert result.exit_code == 0
        for flag in ("--host", "--port", "--reload"):
            assert flag in result.output
