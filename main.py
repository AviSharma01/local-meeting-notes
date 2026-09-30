import functools
from datetime import date, datetime
from enum import Enum
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from src.action_items import action_items_section_exists, append_action_items
from src.note_writer import note_stem, write_markdown_note
from src.ollama_client import DEFAULT_MODEL, extract_debrief, extract_meeting
from src.related_notes import (
    find_related_notes,
    format_related_meetings_section,
    load_meeting_notes,
)
from src.renderer import render_debrief, render_meeting
from src.transcript_cleaner import clean_transcript
from src.transcripts import read_transcript
from src.transcriber import (
    AUDIO_EXTENSIONS,
    format_transcript,
    transcribe_audio,
    write_transcript,
)


app = typer.Typer(help="Local-first meeting notes CLI.")
# Markup is off so transcript and model text such as "[laughs]" prints unchanged.
console = Console(markup=False)

WHISPER_MODEL_HELP = (
    "Local faster-whisper model to use. "
    "base is faster for testing; small may improve quality but is slower."
)


class WhisperModelSize(str, Enum):
    tiny = "tiny"
    base = "base"
    small = "small"
    medium = "medium"


class Mode(str, Enum):
    meeting = "meeting"
    debrief = "debrief"


def report_errors(command):
    """Report expected failures as a red message instead of a traceback."""

    @functools.wraps(command)
    def wrapper(*args, **kwargs):
        try:
            return command(*args, **kwargs)
        except (RuntimeError, ValueError, OSError) as error:
            console.print(str(error), style="red")
            raise typer.Exit(code=1) from error

    return wrapper


def format_meeting_note(
    title: str,
    model: str,
    generated_notes: str,
    note_date: date,
    source: str,
) -> str:
    """Wrap generated notes with Phase 1 Obsidian-friendly metadata."""
    cleaned_notes = generated_notes.strip()
    return (
        "---\n"
        "type: meeting-note\n"
        f"date: {note_date.isoformat()}\n"
        f"source: {source}\n"
        f"model: {model}\n"
        "tags:\n"
        "  - meeting-notes\n"
        "---\n\n"
        f"# Meeting Notes: {title}\n\n"
        f"{cleaned_notes}"
    )


def format_debrief_note(
    title: str,
    company: str,
    model: str,
    generated_notes: str,
    note_date: date,
    source: str,
) -> str:
    """Wrap a rendered debrief with Obsidian-friendly metadata."""
    cleaned_notes = generated_notes.strip()
    return (
        "---\n"
        "type: debrief\n"
        f"date: {note_date.isoformat()}\n"
        f"company: {company}\n"
        f"source: {source}\n"
        f"model: {model}\n"
        "tags:\n"
        "  - debrief\n"
        "---\n\n"
        f"# Debrief: {title}\n\n"
        f"{cleaned_notes}"
    )


@app.callback()
def main() -> None:
    """Local-first meeting notes CLI."""


@app.command()
@report_errors
def preview(transcript_path: Path) -> None:
    """Print a local .txt transcript preview."""
    transcript = read_transcript(transcript_path)
    cleaned_transcript = clean_transcript(transcript)
    console.print(
        Panel(
            cleaned_transcript,
            title=Text(str(transcript_path)),
            border_style="cyan",
        )
    )


@app.command()
@report_errors
def transcribe(
    audio_path: Path,
    out: Path = typer.Option(..., "--out", help="Output folder for the transcript."),
    model: WhisperModelSize = typer.Option(
        WhisperModelSize.base,
        "--model",
        help=WHISPER_MODEL_HELP,
    ),
) -> None:
    """Transcribe a local audio file to timestamped plain text."""
    with console.status("Transcribing audio..."):
        segments = transcribe_audio(audio_path, model_size=model.value)
    transcript_path = write_transcript(out, audio_path, segments)
    console.print(f"Saved transcript: {transcript_path}")


@app.command()
@report_errors
def summarize(
    input_path: Path,
    title: str | None = typer.Option(
        None,
        "--title",
        help="Title for the saved note. Required in meeting mode; "
        "defaults to '<Company> debrief' in debrief mode.",
    ),
    out: Path = typer.Option(..., "--out", help="Output folder for the Markdown note."),
    mode: Mode = typer.Option(Mode.meeting, "--mode", help="Kind of note to write."),
    company: str | None = typer.Option(
        None,
        "--company",
        help="Company the debrief is about. Required in debrief mode.",
    ),
    model: str = typer.Option(DEFAULT_MODEL, "--model", help="Local Ollama model to use."),
    note_date: datetime | None = typer.Option(
        None,
        "--date",
        formats=["%Y-%m-%d"],
        help="Note date in YYYY-MM-DD form. Defaults to today.",
    ),
    whisper_model: WhisperModelSize = typer.Option(
        WhisperModelSize.base,
        "--whisper-model",
        help=f"{WHISPER_MODEL_HELP} Used only for audio input.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite an existing note for this date and title.",
    ),
    link_related: bool = typer.Option(
        False,
        "--link-related",
        help="Link related meeting notes from the output folder.",
    ),
) -> None:
    """Generate and save Markdown meeting notes from a transcript or audio file."""
    if mode is Mode.debrief:
        if not company:
            raise ValueError("--company is required with --mode debrief.")
        title = title or f"{company} debrief"
    else:
        if company:
            raise ValueError("--company is only used with --mode debrief.")
        if not title:
            raise ValueError("--title is required in meeting mode.")

    selected_date = note_date.date() if note_date else date.today()
    stem = note_stem(selected_date, title)
    note_path = out / f"{stem}.md"

    if note_path.exists() and not force:
        raise ValueError(f"Note already exists: {note_path}. Pass --force to overwrite it.")

    if input_path.suffix.lower() in AUDIO_EXTENSIONS:
        with console.status("Transcribing audio..."):
            segments = transcribe_audio(input_path, model_size=whisper_model.value)
        transcript_path = write_transcript(
            out / "transcripts",
            input_path,
            segments,
            stem=stem,
        )
        console.print(f"Saved transcript: {transcript_path}")
        transcript = format_transcript(segments)
        source = "audio"
    else:
        transcript = read_transcript(input_path)
        source = "transcript"

    cleaned_transcript = clean_transcript(transcript)
    if mode is Mode.debrief:
        with console.status("Generating notes..."):
            extraction = extract_debrief(cleaned_transcript, model=model)
        notes = format_debrief_note(
            title,
            company,
            model,
            render_debrief(extraction),
            selected_date,
            source,
        )
        action_items = extraction.commitments
    else:
        with console.status("Generating notes..."):
            extraction = extract_meeting(cleaned_transcript, model=model)
        notes = format_meeting_note(
            title,
            model,
            render_meeting(extraction),
            selected_date,
            source,
        )
        action_items = extraction.action_items
    related_status = None

    if link_related:
        candidate_notes = load_meeting_notes(out)
        related_matches = find_related_notes(
            title,
            notes,
            candidate_notes,
            current_stem=stem,
        )
        related_section = format_related_meetings_section(related_matches)
        if related_section:
            notes = f"{notes}\n\n{related_section}"
            related_status = f"Added related meetings: {len(related_matches)}"
        else:
            related_status = "No related meetings found."

    saved_path = write_markdown_note(str(out), stem, notes)

    console.print(
        Panel(
            notes,
            title=Text(title),
            border_style="green",
        )
    )
    console.print(f"Saved note: {saved_path}")
    if related_status:
        console.print(related_status)

    if not action_items:
        console.print("No action items found; Action Items.md was not updated.")
    elif action_items_section_exists(out, stem):
        console.print(
            f"Action items for [[{stem}]] already exist; Action Items.md was not updated."
        )
    else:
        action_items_path = append_action_items(out, stem, action_items)
        console.print(f"Updated action items: {action_items_path}")


if __name__ == "__main__":
    app()
