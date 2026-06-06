from pathlib import Path


def read_transcript(transcript_path: Path) -> str:
    """Read a user-provided .txt transcript path."""
    if transcript_path.suffix.lower() != ".txt":
        raise ValueError("Transcript path must point to a .txt file.")

    return transcript_path.read_text(encoding="utf-8")
