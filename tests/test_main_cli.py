from pathlib import Path

from typer.testing import CliRunner

import main
from src.note_writer import safe_filename


runner = CliRunner()


def test_preview_command_still_works():
    result = runner.invoke(
        main.app,
        ["preview", "tests/fixtures/sample_meeting_short.txt"],
    )

    assert result.exit_code == 0
    assert "Alex: Let's start with the launch checklist." in result.output


def test_summarize_command_generates_and_saves_note(monkeypatch, tmp_path):
    generated_notes = "# Summary\n\nLaunch stays on track."
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
    assert note_path.read_text(encoding="utf-8") == generated_notes
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
