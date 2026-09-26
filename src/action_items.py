from pathlib import Path

from src.models import ActionItem
from src.renderer import render_action_item


ACTION_ITEMS_FILENAME = "Action Items.md"


def action_items_section_exists(folder_path: str | Path, note_stem: str) -> bool:
    """Report whether Action Items.md already has a section for a note."""
    action_items_path = Path(folder_path) / ACTION_ITEMS_FILENAME
    if not action_items_path.exists():
        return False

    return _section_heading(note_stem) in action_items_path.read_text(encoding="utf-8")


def append_action_items(
    folder_path: str,
    note_stem: str,
    action_items: list[ActionItem],
) -> Path | None:
    """Append action items to Action Items.md in a selected folder."""
    if not action_items:
        return None

    folder = Path(folder_path)
    folder.mkdir(parents=True, exist_ok=True)

    action_items_path = folder / ACTION_ITEMS_FILENAME
    section = _format_action_items_section(note_stem, action_items)

    if action_items_path.exists():
        existing_content = action_items_path.read_text(encoding="utf-8")
        separator = "\n\n" if existing_content and not existing_content.endswith("\n\n") else ""
        action_items_path.write_text(
            f"{existing_content}{separator}{section}",
            encoding="utf-8",
        )
    else:
        action_items_path.write_text(section, encoding="utf-8")

    return action_items_path


def _section_heading(note_stem: str) -> str:
    return f"## From [[{note_stem}]]"


def _format_action_items_section(note_stem: str, action_items: list[ActionItem]) -> str:
    source_line = f"  - Source: [[{note_stem}]]"
    formatted_items = [f"{render_action_item(item)}\n{source_line}" for item in action_items]

    return f"{_section_heading(note_stem)}\n\n" + "\n\n".join(formatted_items)
