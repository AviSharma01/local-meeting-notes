from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from src.note_writer import write_markdown_note
from src.ollama_client import generate_meeting_notes
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


@app.command()
def summarize(
    transcript_path: Path,
    title: str = typer.Option(..., "--title", help="Meeting title for the saved note."),
    out: Path = typer.Option(..., "--out", help="Output folder for the Markdown note."),
    model: str = typer.Option("qwen2.5:7b", "--model", help="Local Ollama model to use."),
) -> None:
    """Generate and save Markdown meeting notes."""
    transcript = read_transcript(transcript_path)
    cleaned_transcript = clean_transcript(transcript)
    notes = generate_meeting_notes(cleaned_transcript, model=model)
    saved_path = write_markdown_note(str(out), title, notes)

    console.print(
        Panel(
            notes,
            title=title,
            border_style="green",
        )
    )
    console.print(f"Saved note: {saved_path}")


if __name__ == "__main__":
    app()
