from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MeetingNote:
    title: str
    filename: str
    path: Path
    content: str


def load_meeting_notes(folder_path: str | Path) -> list[MeetingNote]:
    """Load direct Markdown meeting notes from an explicitly selected folder."""
    folder = Path(folder_path)
    if not folder.exists() or not folder.is_dir():
        return []

    meeting_notes = []
    for path in sorted(folder.iterdir(), key=lambda child: child.name.lower()):
        if path.is_symlink():
            continue
        if not path.is_file():
            continue
        if path.name == "Action Items.md":
            continue
        if path.suffix.lower() != ".md":
            continue

        content = path.read_text(encoding="utf-8")
        meeting_notes.append(
            MeetingNote(
                title=_extract_title(content, path),
                filename=path.name,
                path=path,
                content=content,
            )
        )

    return meeting_notes


def _extract_title(content: str, path: Path) -> str:
    for line in content.splitlines():
        stripped_line = line.lstrip()
        if stripped_line.startswith("# "):
            title = stripped_line[2:].strip()
            if title:
                return title

    return path.stem
