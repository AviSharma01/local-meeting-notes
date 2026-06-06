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
    assert note_path.read_text(encoding="utf-8") == generated_notes


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
