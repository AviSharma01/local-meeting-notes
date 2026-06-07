from src.related_notes import MeetingNote, load_meeting_notes


def test_load_meeting_notes_loads_direct_markdown_notes(tmp_path):
    note_path = tmp_path / "sprint-planning.md"
    content = "# Meeting Notes: Sprint Planning\n\n## Summary\n\nDiscussed sprint scope."
    note_path.write_text(content, encoding="utf-8")

    notes = load_meeting_notes(tmp_path)

    assert notes == [
        MeetingNote(
            title="Meeting Notes: Sprint Planning",
            filename="sprint-planning.md",
            path=note_path,
            content=content,
        )
    ]


def test_load_meeting_notes_ignores_action_items_file(tmp_path):
    (tmp_path / "Action Items.md").write_text("# Action Items", encoding="utf-8")
    (tmp_path / "meeting.md").write_text("# Meeting", encoding="utf-8")

    notes = load_meeting_notes(tmp_path)

    assert [note.filename for note in notes] == ["meeting.md"]


def test_load_meeting_notes_ignores_non_markdown_files(tmp_path):
    (tmp_path / "meeting.md").write_text("# Meeting", encoding="utf-8")
    (tmp_path / "transcript.txt").write_text("# Not Markdown", encoding="utf-8")

    notes = load_meeting_notes(tmp_path)

    assert [note.filename for note in notes] == ["meeting.md"]


def test_load_meeting_notes_does_not_recurse_into_subfolders(tmp_path):
    subfolder = tmp_path / "archive"
    subfolder.mkdir()
    (subfolder / "old-meeting.md").write_text("# Old Meeting", encoding="utf-8")

    assert load_meeting_notes(tmp_path) == []


def test_load_meeting_notes_does_not_follow_symlinks(tmp_path):
    real_note = tmp_path / "real-meeting.md"
    real_note.write_text("# Real Meeting", encoding="utf-8")
    symlink_note = tmp_path / "linked-meeting.md"
    symlink_note.symlink_to(real_note)

    notes = load_meeting_notes(tmp_path)

    assert [note.filename for note in notes] == ["real-meeting.md"]


def test_load_meeting_notes_returns_empty_list_for_missing_folder(tmp_path):
    assert load_meeting_notes(tmp_path / "missing") == []


def test_load_meeting_notes_extracts_title_from_first_h1_heading(tmp_path):
    (tmp_path / "meeting.md").write_text(
        "Intro text\n# Meeting Notes: Launch Sync\n# Later H1",
        encoding="utf-8",
    )

    notes = load_meeting_notes(tmp_path)

    assert notes[0].title == "Meeting Notes: Launch Sync"


def test_load_meeting_notes_falls_back_to_filename_stem_without_h1(tmp_path):
    (tmp_path / "launch-sync.md").write_text(
        "## Summary\n\nNo H1 heading.",
        encoding="utf-8",
    )

    notes = load_meeting_notes(tmp_path)

    assert notes[0].title == "launch-sync"


def test_load_meeting_notes_sorts_results_by_filename(tmp_path):
    (tmp_path / "beta.md").write_text("# Beta", encoding="utf-8")
    (tmp_path / "Alpha.md").write_text("# Alpha", encoding="utf-8")
    (tmp_path / "charlie.md").write_text("# Charlie", encoding="utf-8")

    notes = load_meeting_notes(tmp_path)

    assert [note.filename for note in notes] == ["Alpha.md", "beta.md", "charlie.md"]
