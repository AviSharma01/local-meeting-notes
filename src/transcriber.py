from dataclasses import dataclass
from pathlib import Path

from src.note_writer import safe_filename


@dataclass(frozen=True)
class TranscriptSegment:
    start_seconds: int | float
    text: str


def format_timestamp(seconds: int | float) -> str:
    """Format segment start seconds as a transcript timestamp."""
    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    remaining_seconds = total_seconds % 60

    if hours:
        return f"[{hours:02d}:{minutes:02d}:{remaining_seconds:02d}]"

    return f"[{minutes:02d}:{remaining_seconds:02d}]"


def format_transcript(segments: list[TranscriptSegment]) -> str:
    """Format transcript segments as timestamped plain text."""
    return "\n".join(
        f"{format_timestamp(segment.start_seconds)} {segment.text.strip()}"
        for segment in segments
        if segment.text.strip()
    )


def transcript_filename(audio_path: str | Path) -> str:
    """Generate a safe .txt transcript filename from an audio path."""
    return safe_filename(Path(audio_path).stem, extension=".txt")


def write_transcript(
    folder_path: str | Path,
    audio_path: str | Path,
    segments: list[TranscriptSegment],
) -> Path:
    """Write a timestamped transcript to an explicitly selected folder."""
    folder = Path(folder_path)
    folder.mkdir(parents=True, exist_ok=True)

    transcript_path = folder / transcript_filename(audio_path)
    transcript_path.write_text(format_transcript(segments), encoding="utf-8")

    return transcript_path


def transcribe_audio(audio_path: str | Path) -> list[TranscriptSegment]:
    """Placeholder boundary for a future local transcription engine."""
    raise RuntimeError(
        "Local transcription is not configured yet. "
        "A local transcription engine will be added in a later Phase 4 task."
    )
