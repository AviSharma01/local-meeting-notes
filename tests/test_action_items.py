from src.action_items import action_items_section_exists, append_action_items
from src.models import ActionItem


def test_append_action_items_creates_action_items_file(tmp_path):
    action_items_path = append_action_items(
        str(tmp_path),
        "Sample Meeting",
        [ActionItem(task="Send notes", owner="Avi", due="Friday")],
    )

    assert action_items_path == tmp_path / "Action Items.md"
    assert action_items_path.exists()


def test_append_action_items_writes_items_from_objects(tmp_path):
    append_action_items(
        str(tmp_path),
        "Sample Meeting",
        [
            ActionItem(task="Send notes", owner="Avi", due="Friday", evidence="[00:12]"),
            ActionItem(task="Review QA plan"),
        ],
    )

    content = (tmp_path / "Action Items.md").read_text(encoding="utf-8")
    assert content == (
        "## From [[Sample Meeting]]\n"
        "\n"
        "- [ ] Send notes — Owner: Avi — Due: Friday\n"
        "  - Evidence: [00:12]\n"
        "  - Source: [[Sample Meeting]]\n"
        "\n"
        "- [ ] Review QA plan — Owner: Unknown — Due: Unknown\n"
        "  - Source: [[Sample Meeting]]"
    )


def test_append_action_items_preserves_existing_content(tmp_path):
    action_items_path = tmp_path / "Action Items.md"
    existing_content = "# Action Items\n\nExisting content."
    action_items_path.write_text(existing_content, encoding="utf-8")

    append_action_items(
        str(tmp_path),
        "Sample Meeting",
        [ActionItem(task="Send notes", owner="Avi", due="Friday")],
    )

    content = action_items_path.read_text(encoding="utf-8")
    assert content.startswith(existing_content + "\n\n")
    assert "- [ ] Send notes" in content


def test_append_action_items_returns_none_and_creates_no_file_when_none_exist(tmp_path):
    result = append_action_items(str(tmp_path), "Sample Meeting", [])

    assert result is None
    assert not (tmp_path / "Action Items.md").exists()


def test_append_action_items_adds_source_line(tmp_path):
    append_action_items(
        str(tmp_path),
        "Sample Meeting",
        [ActionItem(task="Send notes", owner="Avi", due="Friday")],
    )

    content = (tmp_path / "Action Items.md").read_text(encoding="utf-8")
    assert "  - Source: [[Sample Meeting]]" in content


def test_append_action_items_links_the_note_stem(tmp_path):
    append_action_items(
        str(tmp_path),
        "2026-01-15-sample-meeting",
        [ActionItem(task="Send notes", owner="Avi", due="Friday")],
    )

    content = (tmp_path / "Action Items.md").read_text(encoding="utf-8")
    assert "## From [[2026-01-15-sample-meeting]]" in content
    assert "  - Source: [[2026-01-15-sample-meeting]]" in content


def test_action_items_section_exists_is_false_without_the_file(tmp_path):
    assert action_items_section_exists(tmp_path, "2026-01-15-sample-meeting") is False


def test_action_items_section_exists_finds_an_appended_section(tmp_path):
    append_action_items(
        str(tmp_path),
        "2026-01-15-sample-meeting",
        [ActionItem(task="Send notes")],
    )

    assert action_items_section_exists(tmp_path, "2026-01-15-sample-meeting") is True


def test_action_items_section_exists_separates_dates_for_one_title(tmp_path):
    append_action_items(
        str(tmp_path),
        "2026-01-15-sample-meeting",
        [ActionItem(task="Send notes")],
    )

    assert action_items_section_exists(tmp_path, "2026-02-01-sample-meeting") is False
