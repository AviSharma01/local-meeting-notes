import re
from pathlib import Path


UNSAFE_FILENAME_CHARS = r'[/:?*"<>|]'


def safe_filename(title: str, extension: str = ".md") -> str:
    """Convert a meeting title into a safe Markdown filename."""
    normalized_extension = extension if extension.startswith(".") else f".{extension}"
    safe_title = re.sub(UNSAFE_FILENAME_CHARS, " ", title.strip())
    safe_title = re.sub(r"[\s_-]+", "-", safe_title)
    safe_title = safe_title.strip("-").lower()

    if not safe_title:
        safe_title = "meeting-notes"

    if safe_title.endswith(normalized_extension):
        return safe_title

    return f"{safe_title}{normalized_extension}"


def write_markdown_note(folder_path: str, title: str, content: str) -> Path:
    """Write Markdown content to an explicitly selected folder."""
    folder = Path(folder_path)
    folder.mkdir(parents=True, exist_ok=True)

    note_path = folder / safe_filename(title)
    note_path.write_text(content, encoding="utf-8")

    return note_path
