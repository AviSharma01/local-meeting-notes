from pathlib import Path

from typer.testing import CliRunner

import main
from src.note_writer import safe_filename
from src.transcriber import TranscriptSegment


runner = CliRunner()


def test_preview_command_still_works():
    result = runner.invoke(
        main.app,
        ["preview", "tests/fixtures/sample_meeting_short.txt"],
    )

    assert result.exit_code == 0
    assert "Alex: Let's start with the launch checklist." in result.output


def test_transcribe_command_help_is_available():
    result = runner.invoke(main.app, ["transcribe", "--help"])

    assert result.exit_code == 0
    assert "Transcribe a local audio file" in result.output
    assert "--out" in result.output
    assert "--model" in result.output
    assert "base is faster" in result.output
    assert "for testing" in result.output
    assert "small may improve quality" in result.output


def test_transcribe_command_writes_mocked_transcript(monkeypatch, tmp_path):
    captured = {}

    def fake_transcribe_audio(audio_path, model_size):
        assert str(audio_path) == "meeting.m4a"
        captured["model_size"] = model_size
        return [
            TranscriptSegment(0, "First transcribed segment."),
            TranscriptSegment(18, "Second transcribed segment."),
        ]

    monkeypatch.setattr(main, "transcribe_audio", fake_transcribe_audio)

    result = runner.invoke(
        main.app,
        [
            "transcribe",
            "meeting.m4a",
            "--out",
            str(tmp_path),
        ],
    )

    transcript_path = tmp_path / "meeting.txt"

    assert result.exit_code == 0
    assert captured["model_size"] == "base"
    assert transcript_path.exists()
    assert transcript_path.read_text(encoding="utf-8") == (
        "[00:00] First transcribed segment.\n"
        "[00:18] Second transcribed segment."
    )
    assert "Saved transcript:" in result.output
    assert "meeting.txt" in result.output


def test_transcribe_command_passes_selected_model(monkeypatch, tmp_path):
    captured = {}

    def fake_transcribe_audio(audio_path, model_size):
        captured["model_size"] = model_size
        return [TranscriptSegment(0, "First transcribed segment.")]

    monkeypatch.setattr(main, "transcribe_audio", fake_transcribe_audio)

    result = runner.invoke(
        main.app,
        [
            "transcribe",
            "meeting.m4a",
            "--out",
            str(tmp_path),
            "--model",
            "small",
        ],
    )

    assert result.exit_code == 0
    assert captured["model_size"] == "small"
    assert (tmp_path / "meeting.txt").exists()


def test_summarize_command_generates_and_saves_note(monkeypatch, tmp_path):
    generated_notes = "\n\n# Summary\n\nLaunch stays on track.\n\n"
    captured = {}

    def fake_generate_meeting_notes(transcript, model):
        captured["transcript"] = transcript
        captured["model"] = model
        return generated_notes

    monkeypatch.setattr(main, "generate_meeting_notes", fake_generate_meeting_notes)

    result = runner.invoke(
        main.app,
        [
            "summarize",
            "tests/fixtures/sample_meeting_short.txt",
            "--title",
            "Sample Meeting",
            "--out",
            str(tmp_path),
        ],
    )

    note_path = tmp_path / safe_filename("Sample Meeting")

    assert result.exit_code == 0
    assert captured["model"] == "qwen2.5:7b"
    assert "Alex: Let's start with the launch checklist." in captured["transcript"]
    assert "\n\n" not in captured["transcript"]
    assert "# Summary" in result.output
    assert "Launch stays on track." in result.output
    assert "sample-meeting.md" in result.output
    assert "No action items found; Action Items.md was not updated." in result.output
    saved_note = note_path.read_text(encoding="utf-8")
    assert saved_note.startswith("---\n")
    assert "type: meeting-note" in saved_note
    assert "source: local-transcript" in saved_note
    assert "model: qwen2.5:7b" in saved_note
    assert "tags:\n  - meeting-notes" in saved_note
    assert "# Meeting Notes: Sample Meeting" in saved_note
    assert "# Summary\n\nLaunch stays on track." in saved_note
    assert saved_note.endswith("Launch stays on track.")
    assert "```" not in saved_note
    assert not (tmp_path / "Action Items.md").exists()


def test_summarize_command_passes_selected_model(monkeypatch, tmp_path):
    captured = {}

    def fake_generate_meeting_notes(transcript, model):
        captured["model"] = model
        return "# Summary\n\nCustom model used."

    monkeypatch.setattr(main, "generate_meeting_notes", fake_generate_meeting_notes)

    result = runner.invoke(
        main.app,
        [
            "summarize",
            "tests/fixtures/sample_meeting_short.txt",
            "--title",
            "Sample Meeting",
            "--out",
            str(tmp_path),
            "--model",
            "test-model",
        ],
    )

    assert result.exit_code == 0
    assert captured["model"] == "test-model"
    saved_note = (tmp_path / safe_filename("Sample Meeting")).read_text(
        encoding="utf-8"
    )
    assert "model: test-model" in saved_note


def test_summarize_command_uses_out_as_output_folder(monkeypatch, tmp_path):
    monkeypatch.setattr(
        main,
        "generate_meeting_notes",
        lambda transcript, model: "# Summary\n\nSaved to nested folder.",
    )
    out = tmp_path / "nested" / "meetings"

    result = runner.invoke(
        main.app,
        [
            "summarize",
            "tests/fixtures/sample_meeting_short.txt",
            "--title",
            "Nested Meeting",
            "--out",
            str(out),
        ],
    )

    assert result.exit_code == 0
    assert (out / Path("nested-meeting.md")).exists()


def test_summarize_command_appends_action_items(monkeypatch, tmp_path):
    generated_notes = """# Summary

Launch planning happened.

## Action Items

- [ ] Send launch notes — Owner: Avi — Due: Friday
  - Evidence: Avi agreed to send notes.
"""

    monkeypatch.setattr(
        main,
        "generate_meeting_notes",
        lambda transcript, model: generated_notes,
    )

    result = runner.invoke(
        main.app,
        [
            "summarize",
            "tests/fixtures/sample_meeting_short.txt",
            "--title",
            "Sample Meeting",
            "--out",
            str(tmp_path),
        ],
    )

    note_path = tmp_path / safe_filename("Sample Meeting")
    action_items_path = tmp_path / "Action Items.md"

    assert result.exit_code == 0
    assert note_path.exists()
    assert action_items_path.exists()
    assert "sample-meeting.md" in result.output
    assert "Updated action items:" in result.output
    assert "Action Items.md" in result.output

    action_items_content = action_items_path.read_text(encoding="utf-8")
    assert "## From [[Sample Meeting]]" in action_items_content
    assert "- [ ] Send launch notes" in action_items_content
    assert "  - Source: [[Sample Meeting]]" in action_items_content

    saved_note = note_path.read_text(encoding="utf-8")
    assert "# Meeting Notes: Sample Meeting" in saved_note
    assert "- [ ] Send launch notes" in saved_note


def test_summarize_command_does_not_create_action_items_when_none_found(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        main,
        "generate_meeting_notes",
        lambda transcript, model: "# Summary\n\nNo action items today.",
    )

    result = runner.invoke(
        main.app,
        [
            "summarize",
            "tests/fixtures/sample_meeting_short.txt",
            "--title",
            "Sample Meeting",
            "--out",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert (tmp_path / safe_filename("Sample Meeting")).exists()
    assert not (tmp_path / "Action Items.md").exists()
    assert "sample-meeting.md" in result.output
    assert "No action items found; Action Items.md was not updated." in result.output


def test_summarize_command_does_not_load_related_notes_without_flag(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        main,
        "generate_meeting_notes",
        lambda transcript, model: "# Summary\n\nLaunch stays on track.",
    )

    def fail_if_called(out):
        raise AssertionError("load_meeting_notes should not be called")

    monkeypatch.setattr(main, "load_meeting_notes", fail_if_called)

    result = runner.invoke(
        main.app,
        [
            "summarize",
            "tests/fixtures/sample_meeting_short.txt",
            "--title",
            "Sample Meeting",
            "--out",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "No related meetings found." not in result.output


def test_summarize_command_link_related_adds_related_meetings_section(
    monkeypatch,
    tmp_path,
):
    previous_note = tmp_path / "sample-retro.md"
    previous_note.write_text(
        """---
tags: [launch]
---

# Sample Retro

## Summary

Discussed launch QA.
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        main,
        "generate_meeting_notes",
        lambda transcript, model: "# Summary\n\nLaunch QA stayed on track.",
    )

    result = runner.invoke(
        main.app,
        [
            "summarize",
            "tests/fixtures/sample_meeting_short.txt",
            "--title",
            "Sample Meeting",
            "--out",
            str(tmp_path),
            "--link-related",
        ],
    )

    saved_note = (tmp_path / safe_filename("Sample Meeting")).read_text(
        encoding="utf-8"
    )

    assert result.exit_code == 0
    assert "Added related meetings: 1" in result.output
    assert "## Related Meetings" in saved_note
    assert "[[sample-retro]]" in saved_note


def test_summarize_command_link_related_with_no_matches_adds_no_empty_section(
    monkeypatch,
    tmp_path,
):
    previous_note = tmp_path / "budget-review.md"
    previous_note.write_text(
        "# Budget Review\n\n## Summary\n\nDiscussed finance forecasts.",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        main,
        "generate_meeting_notes",
        lambda transcript, model: "# Summary\n\nLaunch QA stayed on track.",
    )

    result = runner.invoke(
        main.app,
        [
            "summarize",
            "tests/fixtures/sample_meeting_short.txt",
            "--title",
            "Sample Meeting",
            "--out",
            str(tmp_path),
            "--link-related",
        ],
    )

    saved_note = (tmp_path / safe_filename("Sample Meeting")).read_text(
        encoding="utf-8"
    )

    assert result.exit_code == 0
    assert "No related meetings found." in result.output
    assert "## Related Meetings" not in saved_note


def test_summarize_command_appends_action_items_when_related_meetings_are_added(
    monkeypatch,
    tmp_path,
):
    (tmp_path / "sample-retro.md").write_text(
        "# Sample Retro\n\n## Summary\n\nDiscussed launch QA.",
        encoding="utf-8",
    )
    generated_notes = """# Summary

Launch QA stayed on track.

## Action Items

- [ ] Send launch notes — Owner: Avi — Due: Friday
  - Evidence: Avi agreed to send notes.
"""
    monkeypatch.setattr(
        main,
        "generate_meeting_notes",
        lambda transcript, model: generated_notes,
    )

    result = runner.invoke(
        main.app,
        [
            "summarize",
            "tests/fixtures/sample_meeting_short.txt",
            "--title",
            "Sample Meeting",
            "--out",
            str(tmp_path),
            "--link-related",
        ],
    )

    saved_note = (tmp_path / safe_filename("Sample Meeting")).read_text(
        encoding="utf-8"
    )
    action_items_content = (tmp_path / "Action Items.md").read_text(encoding="utf-8")

    assert result.exit_code == 0
    assert "## Related Meetings" in saved_note
    assert "- [ ] Send launch notes" in action_items_content
    assert "  - Source: [[Sample Meeting]]" in action_items_content
