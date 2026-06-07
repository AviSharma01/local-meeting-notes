from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MeetingNote:
    title: str
    filename: str
    path: Path
    content: str
    tags: list[str]
    summary: str
    date: str | None


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
        frontmatter_lines = _extract_frontmatter(content)
        meeting_notes.append(
            MeetingNote(
                title=_extract_title(content, path),
                filename=path.name,
                path=path,
                content=content,
                tags=_extract_tags(frontmatter_lines),
                summary=_extract_summary(content),
                date=_extract_date(frontmatter_lines),
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


def _extract_frontmatter(content: str) -> list[str]:
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return []

    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return lines[1:index]

    return []


def _extract_tags(frontmatter_lines: list[str]) -> list[str]:
    tags = []
    in_tags_list = False

    for line in frontmatter_lines:
        stripped_line = line.strip()

        if stripped_line.startswith("tags:"):
            in_tags_list = True
            tag_value = stripped_line.removeprefix("tags:").strip()
            if tag_value.startswith("[") and tag_value.endswith("]"):
                return [
                    _clean_yaml_value(tag)
                    for tag in tag_value[1:-1].split(",")
                    if _clean_yaml_value(tag)
                ]
            if tag_value:
                return [_clean_yaml_value(tag_value)]
            continue

        if in_tags_list:
            if stripped_line.startswith("- "):
                tag = _clean_yaml_value(stripped_line.removeprefix("- ").strip())
                if tag:
                    tags.append(tag)
            elif stripped_line:
                break

    return tags


def _extract_date(frontmatter_lines: list[str]) -> str | None:
    for line in frontmatter_lines:
        stripped_line = line.strip()
        if stripped_line.startswith("date:"):
            date = _clean_yaml_value(stripped_line.removeprefix("date:").strip())
            return date or None

    return None


def _extract_summary(content: str) -> str:
    summary_lines = []
    in_summary = False

    for line in content.splitlines():
        if line.strip() == "## Summary":
            in_summary = True
            continue

        if in_summary and line.startswith("## "):
            break

        if in_summary:
            summary_lines.append(line)

    return "\n".join(summary_lines).strip()


def _clean_yaml_value(value: str) -> str:
    return value.strip().strip("\"'")
