from dataclasses import dataclass
from pathlib import Path
import re


STOP_WORDS = {
    "the",
    "and",
    "but",
    "for",
    "with",
    "just",
    "can",
    "will",
    "would",
    "should",
    "could",
    "really",
    "very",
    "more",
    "most",
    "about",
    "into",
    "from",
    "that",
    "this",
    "meeting",
    "meetings",
    "notes",
    "summary",
    "summarized",
    "decision",
    "decisions",
    "action",
    "actions",
    "item",
    "items",
    "follow",
    "followup",
    "followups",
    "risk",
    "risks",
    "blocker",
    "blockers",
    "question",
    "questions",
    "review",
    "evidence",
    "timestamp",
    "timestamps",
    "owner",
    "owners",
    "due",
    "source",
    "created",
    "create",
    "date",
    "dates",
    "explicitly",
    "mentioned",
    "none",
    "unknown",
    "made",
    "missing",
    "found",
    "related",
    "score",
    "reason",
    "reasons",
    "section",
    "sections",
    "content",
    "generated",
    "final",
    "note",
    "discussed",
    "reviewed",
    "alex",
    "sam",
    "priya",
}
GENERIC_TAGS = {"meeting-notes"}
KEYWORD_SECTIONS = {
    "Summary",
    "Key Decisions",
    "Action Items",
    "Evidence / Timestamps",
}
NOISY_KEYWORD_SECTIONS = {
    "Meeting Health",
    "Needs Review",
    "Related Meetings",
    "Follow-ups",
    "Risks / Blockers",
    "Open Questions",
}


@dataclass(frozen=True)
class MeetingNote:
    title: str
    filename: str
    path: Path
    content: str
    tags: list[str]
    summary: str
    date: str | None


@dataclass(frozen=True)
class RelatedNoteMatch:
    note: MeetingNote
    score: int
    reasons: list[str]


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


def find_related_notes(
    current_title: str,
    current_content: str,
    candidate_notes: list[MeetingNote],
    limit: int = 3,
) -> list[RelatedNoteMatch]:
    """Find related notes using deterministic local keyword rules."""
    if limit <= 0:
        return []

    current_title_words = _meaningful_words(current_title)
    current_words = _meaningful_words(
        f"{current_title} {_extract_keyword_text(current_content)}"
    )
    matches = []

    for note in candidate_notes:
        if note.title == current_title:
            continue

        score = 0
        reasons = []

        shared_title_words = sorted(current_title_words & _meaningful_words(note.title))
        if shared_title_words:
            score += 3
            reasons.append(f"Shared title keyword: {shared_title_words[0]}")

        current_text = f"{current_title} {current_content}".lower()
        for tag in _scoring_tags(note.tags):
            if tag in _tag_words(current_text):
                score += 2
                reasons.append(f"Shared tag: {tag}")

        candidate_words = _meaningful_words(_extract_keyword_text(note.content))
        shared_content_keywords = sorted(current_words & candidate_words)
        if shared_content_keywords:
            scored_keywords = shared_content_keywords[:5]
            score += len(scored_keywords)
            reasons.append(
                "Shared content keywords: " + ", ".join(scored_keywords)
            )

        if score > 0:
            matches.append(
                RelatedNoteMatch(
                    note=note,
                    score=score,
                    reasons=reasons,
                )
            )

    return sorted(matches, key=lambda match: (-match.score, match.note.filename))[:limit]


def format_wiki_link(note: MeetingNote) -> str:
    """Format a meeting note as an Obsidian wiki-link."""
    return f"[[{Path(note.filename).stem}]]"


def format_related_meetings_section(matches: list[RelatedNoteMatch]) -> str:
    """Format related-note matches as an Obsidian-friendly Markdown section."""
    if not matches:
        return ""

    match_sections = []
    for match in matches:
        lines = [f"- {format_wiki_link(match.note)} — Score: {match.score}"]
        lines.extend(f"  - Reason: {reason}" for reason in match.reasons)
        match_sections.append("\n".join(lines))

    return "## Related Meetings\n\n" + "\n\n".join(match_sections)


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


def _extract_keyword_text(content: str) -> str:
    keyword_lines = []
    current_section = None
    saw_section = False

    for line in content.splitlines():
        if line.startswith("## "):
            saw_section = True
            current_section = line.removeprefix("## ").strip()
            continue

        if current_section in KEYWORD_SECTIONS:
            keyword_lines.append(line)
        elif current_section in NOISY_KEYWORD_SECTIONS:
            continue

    keyword_text = "\n".join(keyword_lines).strip()
    if keyword_text:
        return keyword_text
    if saw_section:
        return ""
    return content


def _clean_yaml_value(value: str) -> str:
    return value.strip().strip("\"'")


def _meaningful_words(text: str) -> set[str]:
    return {
        word
        for word in re.findall(r"[a-z0-9]+", text.lower())
        if len(word) > 2 and word not in STOP_WORDS
    }


def _scoring_tags(tags: list[str]) -> list[str]:
    return sorted(
        tag.lower()
        for tag in tags
        if tag.lower() not in GENERIC_TAGS and tag.lower() not in STOP_WORDS
    )


def _tag_words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))
