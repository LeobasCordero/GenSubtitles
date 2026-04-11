"""
gensubtitles.cli.main
~~~~~~~~~~~~~~~~~~~~~
Typer CLI entry point for subtitle generation.

Exposes run_pipeline() as a polished command with:
  - All 6 flags: --input, --output, --model, --target-lang, --source-lang, --device
  - Progress output: [1/4] Extracting audio... etc.
  - Auto-derived output path when --output omitted
  - Exit code 0 on success, 1 on any error
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

app = typer.Typer(
    help="GenSubtitles — generate .srt subtitles from any video. Offline, no API keys.",
    no_args_is_help=True,
)


@app.callback(invoke_without_command=True, no_args_is_help=True)
def generate(
    ctx: typer.Context,
    video_path: Optional[Path] = typer.Option(
        None,
        "--input",
        "-i",
        help="Path to the input video file (.mp4, .mkv, .avi, .mov, .webm).",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Destination .srt path. Defaults to <input>.srt in the same directory.",
    ),
    model: str = typer.Option(
        "small",
        "--model",
        "-m",
        help="Whisper model size: tiny / base / small / medium / large-v1 / large-v2 / large-v3 / turbo.",
    ),
    target_lang: Optional[str] = typer.Option(
        None,
        "--target-lang",
        "-t",
        help="Target ISO 639-1 language code for translation (e.g. 'es', 'fr'). Omit to keep source language.",
    ),
    source_lang: Optional[str] = typer.Option(
        None,
        "--source-lang",
        "-s",
        help="Source language code. Omit for auto-detection by Whisper.",
    ),
    device: str = typer.Option(
        "auto",
        "--device",
        help="Compute device: auto / cpu / cuda.",
    ),
    output_format: str = typer.Option(
        "srt",
        "--format",
        "-f",
        help="Output subtitle format: srt or ssa.",
    ),
) -> None:
    """Generate subtitles from a video file."""
    # If a subcommand (e.g. 'serve') is being invoked, skip generate logic entirely.
    if ctx.invoked_subcommand is not None:
        return

    # Validate --input existence before importing the pipeline
    if video_path is None:
        typer.echo("Error: Missing option '--input' / '-i'.", err=True)
        raise typer.Exit(code=2)
    if not video_path.is_file():
        typer.echo(f"Error: Input file not found: {video_path}", err=True)
        raise typer.Exit(code=1)

    # Auto-derive output path from input stem when --output not provided
    effective_output: Path = output if output is not None else video_path.with_suffix(".srt")

    def _progress(label: str, current: int, total: int) -> None:
        typer.echo(f"[{current}/{total}] {label}...")

    try:
        # Lazy import — keeps CLI importable even without FFmpeg/GPU installed
        from gensubtitles.core.pipeline import run_pipeline  # noqa: PLC0415

        result = run_pipeline(
            video_path=video_path,
            output_path=effective_output,
            model_size=model,
            target_lang=target_lang,
            source_lang=source_lang,
            device=device,
            progress_callback=_progress,
        )
        if output_format == "ssa":
            from gensubtitles.core.srt_writer import convert_srt_to_ssa  # noqa: PLC0415

            ssa_path = effective_output.with_suffix(".ssa")
            convert_srt_to_ssa(effective_output, ssa_path)
            effective_output.unlink(missing_ok=True)
            effective_output = ssa_path
        typer.echo(
            f"Done: {effective_output} "
            f"({result.segment_count} segments, lang={result.detected_language})"
        )
        raise typer.Exit(code=0)
    except typer.Exit:
        raise
    except FileNotFoundError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)
    except Exception as exc:  # noqa: BLE001
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)


@app.command("translate")
def translate_subtitles(
    input_file: Path = typer.Argument(..., help="Input subtitle file (.srt or .ssa)."),
    target_lang: str = typer.Option(
        ..., "--target-lang", "-t", help="Target ISO 639-1 language code."
    ),
    source_lang: Optional[str] = typer.Option(
        None, "--source-lang", "-s", help="Source language code. Defaults to 'en' if omitted."
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output path. Defaults to <input>_translated.<ext>."
    ),
) -> None:
    """Translate an existing subtitle file (.srt or .ssa) to another language."""
    if not input_file.is_file():
        typer.echo(f"Error: Input file not found: {input_file}", err=True)
        raise typer.Exit(code=1)
    try:
        from gensubtitles.core.translator import translate_file  # noqa: PLC0415

        result_path = translate_file(input_file, target_lang, source_lang, output)
        typer.echo(f"Done: {result_path}")
        raise typer.Exit(code=0)
    except typer.Exit:
        raise
    except Exception as exc:  # noqa: BLE001
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)


@app.command("convert")
def convert_subtitles(
    input_file: Path = typer.Argument(..., help="Input subtitle file (.srt or .ssa)."),
    output_file: Path = typer.Argument(
        ..., help="Output subtitle file (.srt or .ssa). Format inferred from extension."
    ),
) -> None:
    """Convert a subtitle file between formats (.srt \u2194 .ssa)."""
    if not input_file.is_file():
        typer.echo(f"Error: Input file not found: {input_file}", err=True)
        raise typer.Exit(code=1)
    try:
        from gensubtitles.core.srt_writer import convert_ssa_to_srt, convert_srt_to_ssa  # noqa: PLC0415

        src_ext = input_file.suffix.lower()
        dst_ext = output_file.suffix.lower()
        if src_ext == ".srt" and dst_ext in (".ssa", ".ass"):
            convert_srt_to_ssa(input_file, output_file)
        elif src_ext in (".ssa", ".ass") and dst_ext == ".srt":
            convert_ssa_to_srt(input_file, output_file)
        else:
            typer.echo(
                f"Error: Unsupported conversion: {src_ext} \u2192 {dst_ext}. Supported: .srt\u2194.ssa",
                err=True,
            )
            raise typer.Exit(code=1)
        typer.echo(f"Done: {output_file}")
        raise typer.Exit(code=0)
    except typer.Exit:
        raise
    except Exception as exc:  # noqa: BLE001
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1)


@app.command("serve")
def serve(
    host: str = typer.Option(
        "127.0.0.1",
        "--host",
        help="Host address to bind the server to. Defaults to localhost; use 0.0.0.0 explicitly to expose it on all network interfaces.",
    ),
    port: int = typer.Option(
        8000,
        "--port",
        help="Port number to listen on.",
    ),
    reload: bool = typer.Option(
        False,
        "--reload",
        help="Enable auto-reload on code changes (development mode).",
    ),
) -> None:
    """Start the GenSubtitles FastAPI API server via Uvicorn."""
    import uvicorn  # noqa: PLC0415

    typer.echo(f"Starting GenSubtitles API on http://{host}:{port} ...")
    uvicorn.run(
        "gensubtitles.api.main:app",
        host=host,
        port=port,
        reload=reload,
    )


@app.command("gui")
def launch_gui() -> None:
    """Open the GenSubtitles desktop GUI window."""
    try:
        from gensubtitles.gui.main import main as _gui_main  # noqa: PLC0415
    except ImportError:
        typer.echo(
            "Error: GUI dependencies not installed. "
            "Install them with: pip install gensubtitles[gui]",
            err=True,
        )
        raise typer.Exit(code=1)

    _gui_main()


if __name__ == "__main__":
    app()
