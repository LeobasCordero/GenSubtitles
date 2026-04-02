import typer

app = typer.Typer(help="GenSubtitles — automatic subtitle generation.")


@app.command()
def generate(
    input: str = typer.Option(..., "--input", "-i", help="Path to input video file."),
    output: str = typer.Option("output/subtitles.srt", "--output", "-o", help="Output SRT path."),
) -> None:
    """Generate subtitles from a video file."""
    typer.echo("Not yet implemented — coming in a later phase.")
    raise typer.Exit(code=0)


if __name__ == "__main__":
    app()
