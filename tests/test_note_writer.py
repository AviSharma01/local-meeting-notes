from datetime import date

from src.note_writer import note_stem, safe_filename, write_markdown_note


def test_safe_filename_handles_normal_titles():
    assert safe_filename("Sprint Planning") == "sprint-planning.md"


def test_safe_filename_removes_unsafe_characters():
    title = 'Sprint/Planning: QA? * "Beta" <Launch> | Notes'

    assert safe_filename(title) == "sprint-planning-qa-beta-launch-notes.md"


def test_safe_filename_removes_obsidian_link_characters():
    assert safe_filename("Q3 #launch ^v2 [Draft]") == "q3-launch-v2-draft.md"


def test_safe_filename_handles_empty_titles():
    assert safe_filename("") == "meeting-notes.md"
    assert safe_filename("   ") == "meeting-notes.md"


def test_safe_filename_does_not_duplicate_selected_extension():
    assert safe_filename("Sprint Planning.md") == "sprint-planning.md"
    assert safe_filename("Sprint Planning.txt", extension="txt") == "sprint-planning.txt"


def test_note_stem_prefixes_the_slug_with_the_date():
    assert note_stem(date(2026, 1, 15), "Sprint Planning") == "2026-01-15-sprint-planning"


def test_note_stem_uses_the_safe_slug():
    stem = note_stem(date(2026, 1, 15), 'Sprint/Planning: QA? "Beta"')

    assert stem == "2026-01-15-sprint-planning-qa-beta"


def test_note_stem_carries_no_extension_for_a_title_ending_in_md():
    stem = note_stem(date(2026, 1, 15), "Sprint Planning.md")

    assert stem == "2026-01-15-sprint-planning"
    assert not stem.endswith(".md")


def test_note_stem_handles_empty_titles():
    assert note_stem(date(2026, 1, 15), "   ") == "2026-01-15-meeting-notes"


def test_write_markdown_note_writes_a_dated_stem_unchanged(tmp_path):
    note_path = write_markdown_note(
        str(tmp_path), "2026-01-15-sprint-planning", "# Notes"
    )

    assert note_path.name == "2026-01-15-sprint-planning.md"


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
