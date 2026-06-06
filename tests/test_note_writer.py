from src.note_writer import safe_filename, write_markdown_note


def test_safe_filename_handles_normal_titles():
    assert safe_filename("Sprint Planning") == "sprint-planning.md"


def test_safe_filename_removes_unsafe_characters():
    title = 'Sprint/Planning: QA? * "Beta" <Launch> | Notes'

    assert safe_filename(title) == "sprint-planning-qa-beta-launch-notes.md"


def test_safe_filename_handles_empty_titles():
    assert safe_filename("") == "meeting-notes.md"
    assert safe_filename("   ") == "meeting-notes.md"


def test_safe_filename_does_not_duplicate_selected_extension():
    assert safe_filename("Sprint Planning.md") == "sprint-planning.md"
    assert safe_filename("Sprint Planning.txt", extension="txt") == "sprint-planning.txt"


def test_write_markdown_note_creates_markdown_file(tmp_path):
    note_path = write_markdown_note(str(tmp_path), "Sprint Planning", "# Notes")

    assert note_path.exists()
    assert note_path.name == "sprint-planning.md"


def test_write_markdown_note_writes_expected_content(tmp_path):
    content = "# Summary\n\nLaunch stays on track."

    note_path = write_markdown_note(str(tmp_path), "Launch Sync", content)

    assert note_path.read_text(encoding="utf-8") == content


def test_write_markdown_note_creates_output_folder_if_missing(tmp_path):
    folder = tmp_path / "Meetings"

    note_path = write_markdown_note(str(folder), "Roadmap Review", "# Roadmap")

    assert folder.exists()
    assert note_path.exists()
