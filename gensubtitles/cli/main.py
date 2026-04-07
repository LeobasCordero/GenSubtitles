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


@app.command(no_args_is_help=True)
def generate(
    input: Path = typer.Option(
        ...,
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
) -> None:
    """Generate subtitles from a video file."""
    # Auto-derive output path from input stem when --output not provided
    effective_output: Path = output if output is not None else input.with_suffix(".srt")

    def _progress(label: str, current: int, total: int) -> None:
        typer.echo(f"[{current}/{total}] {label}...")

    try:
        # Lazy import — keeps CLI importable even without FFmpeg/GPU installed
        from gensubtitles.core.pipeline import run_pipeline  # noqa: PLC0415

        result = run_pipeline(
            video_path=input,
            output_path=effective_output,
            model_size=model,
            target_lang=target_lang,
            source_lang=source_lang,
            device=device,
            progress_callback=_progress,
        )
        typer.echo(
            f"Done: {result.srt_path} "
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


if __name__ == "__main__":
    app()
