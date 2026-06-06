from pathlib import Path


ACTION_ITEMS_FILENAME = "Action Items.md"


def extract_action_items(markdown_note: str) -> list[str]:
    """Extract top-level checkbox action items from the Action Items section."""
    action_items = []
    current_item = []
    in_action_items_section = False

    def flush_current_item() -> None:
        if current_item:
            action_items.append("\n".join(current_item))
            current_item.clear()

    for line in markdown_note.splitlines():
        if line.strip() == "## Action Items":
            flush_current_item()
            in_action_items_section = True
            continue

        if in_action_items_section and line.startswith("## "):
            flush_current_item()
            in_action_items_section = False
            continue

        if not in_action_items_section:
            continue

        if line.startswith("- [ ]"):
            flush_current_item()
            current_item.append(line)
        elif current_item and line[:1].isspace():
            current_item.append(line)
        else:
            flush_current_item()

    flush_current_item()

    return action_items


def append_action_items(
    folder_path: str,
    meeting_title: str,
    markdown_note: str,
) -> Path | None:
    """Append extracted action items to Action Items.md in a selected folder."""
    action_items = extract_action_items(markdown_note)
    if not action_items:
        return None

    folder = Path(folder_path)
    folder.mkdir(parents=True, exist_ok=True)

    action_items_path = folder / ACTION_ITEMS_FILENAME
    section = _format_action_items_section(meeting_title, action_items)

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


def _format_action_items_section(meeting_title: str, action_items: list[str]) -> str:
    formatted_items = []
    source_line = f"  - Source: [[{meeting_title}]]"

    for item in action_items:
        if "Source:" in item:
            formatted_items.append(item)
        else:
            formatted_items.append(f"{item}\n{source_line}")

    return f"## From [[{meeting_title}]]\n\n" + "\n\n".join(formatted_items)
