from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from src.action_items import append_action_items
from src.note_writer import write_markdown_note
from src.ollama_client import generate_meeting_notes
from src.transcript_cleaner import clean_transcript
from src.transcripts import read_transcript


app = typer.Typer(help="Local-first meeting notes CLI.")
console = Console()


def format_meeting_note(title: str, model: str, generated_notes: str) -> str:
    """Wrap generated notes with Phase 1 Obsidian-friendly metadata."""
    cleaned_notes = generated_notes.strip()
    return (
        "---\n"
        "type: meeting-note\n"
        "source: local-transcript\n"
        f"model: {model}\n"
        "tags:\n"
        "  - meeting-notes\n"
        "---\n\n"
        f"# Meeting Notes: {title}\n\n"
        f"{cleaned_notes}"
    )


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
    generated_notes = generate_meeting_notes(cleaned_transcript, model=model)
    notes = format_meeting_note(title, model, generated_notes)
    saved_path = write_markdown_note(str(out), title, notes)
    action_items_path = append_action_items(out, title, notes)

    console.print(
        Panel(
            notes,
            title=title,
            border_style="green",
        )
    )
    console.print(f"Saved note: {saved_path}")
    if action_items_path:
        console.print(f"Updated action items: {action_items_path}")
    else:
        console.print("No action items found; Action Items.md was not updated.")


if __name__ == "__main__":
    app()
