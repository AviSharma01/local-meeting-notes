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


def transcribe_audio(
    audio_path: str | Path,
    model_size: str = "base",
) -> list[TranscriptSegment]:
    """Transcribe a local audio file with faster-whisper."""
    model = _create_whisper_model(model_size)
    try:
        segments, _info = model.transcribe(str(audio_path))
        return [
            TranscriptSegment(start_seconds=segment.start, text=segment.text.strip())
            for segment in segments
            if segment.text.strip()
        ]
    except Exception as exc:
        raise RuntimeError(
            f"Could not transcribe audio file '{audio_path}'. "
            "Check that the file exists, is a supported audio format, and that "
            "ffmpeg is installed for decoding common audio formats."
        ) from exc


def _create_whisper_model(model_size: str):
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError(
            "faster-whisper is not installed. Install dependencies with "
            "`pip install -r requirements.txt` or install it directly with "
            "`pip install faster-whisper`."
        ) from exc

    return WhisperModel(model_size)
