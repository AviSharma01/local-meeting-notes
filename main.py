from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from src.transcript_cleaner import clean_transcript
from src.transcripts import read_transcript


app = typer.Typer(help="Local-first meeting notes CLI.")
console = Console()


@app.callback()
def main() -> None:
    """Local-first meeting notes CLI."""


@app.command()
def preview(transcript_path: Path) -> None:
    """Print a local .txt transcript preview."""
    transcript = read_transcript(transcript_path)
    cleaned_transcript = clean_transcript(transcript)
    console.print(
        Panel(
            cleaned_transcript,
            title=str(transcript_path),
            border_style="cyan",
        )
    )


if __name__ == "__main__":
    app()
