from datetime import date
from pathlib import Path

import pytest
from typer.testing import CliRunner

import main
from src.models import ActionItem, DebriefExtraction, MeetingExtraction, Person
from src.note_writer import note_stem, safe_filename
from src.transcriber import TranscriptSegment


runner = CliRunner()

NOTE_DATE = "2026-01-15"
SAMPLE_STEM = f"{NOTE_DATE}-sample-meeting"


def make_extraction(summary, action_items=()):
    return MeetingExtraction(
        summary=summary,
        decisions=[],
        action_items=list(action_items),
        follow_ups=[],
        risks=[],
        open_questions=[],
        needs_review=[],
    )


SEND_NOTES = ActionItem(
    task="Send launch notes",
    owner="Avi",
    due="Friday",
    evidence="Avi agreed to send notes.",
)


def fail_if_called(*args, **kwargs):
    raise AssertionError("This should not have been called")


@pytest.fixture
def sample_transcript(tmp_path):
    path = tmp_path / "sample_meeting_short.txt"
    path.write_text(
        "[00:00] Alex: Let's start with the launch checklist.\n"
        "[00:15] Priya: The docs are ready, but QA needs one more pass.\n"
        "[00:35] Sam: I can own the QA pass by Friday.\n"
        "[00:50] Alex: Great. Decision: keep the beta launch date for next Tuesday.\n",
        encoding="utf-8",
    )
    return path


@pytest.fixture
def sample_audio(tmp_path):
    path = tmp_path / "memo.m4a"
    path.write_bytes(b"not really audio")
    return path


def test_preview_command_still_works(sample_transcript):
    result = runner.invoke(
        main.app,
        ["preview", str(sample_transcript)],
    )

    assert result.exit_code == 0
    assert "Alex: Let's start with the launch checklist." in result.output


def assert_reported_without_traceback(result, expected_message):
    """A handled failure exits 1 with a message and no propagated exception."""
    assert result.exit_code == 1
    assert isinstance(result.exception, SystemExit)
    assert expected_message in result.output.replace("\n", "")
    assert "Traceback" not in result.output
    assert "RuntimeError" not in result.output
    assert "ValueError" not in result.output


def test_transcribe_command_reports_a_missing_audio_file(tmp_path):
    result = runner.invoke(
        main.app,
        ["transcribe", str(tmp_path / "missing.m4a"), "--out", str(tmp_path)],
    )

    assert_reported_without_traceback(result, "Audio file not found:")
    assert list(tmp_path.glob("*.txt")) == []


def test_summarize_command_reports_a_missing_audio_file(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "extract_meeting", fail_if_called)

    result = runner.invoke(
        main.app,
        [
            "summarize",
            str(tmp_path / "missing.m4a"),
            "--title",
            "Sample Meeting",
            "--out",
            str(tmp_path),
            "--date",
            NOTE_DATE,
        ],
    )

    assert_reported_without_traceback(result, "Audio file not found:")
    assert list(tmp_path.glob("*.md")) == []


def test_summarize_command_reports_an_ollama_failure(
    monkeypatch, tmp_path, sample_transcript
):
    def fake_extract_meeting(transcript, model):
        raise RuntimeError("Ollama request failed. Is Ollama running locally?")

    monkeypatch.setattr(main, "extract_meeting", fake_extract_meeting)

    result = runner.invoke(
        main.app,
        [
            "summarize",
            str(sample_transcript),
            "--title",
            "Sample Meeting",
            "--out",
            str(tmp_path),
            "--date",
            NOTE_DATE,
        ],
    )

    assert_reported_without_traceback(result, "Is Ollama running locally?")
    assert not (tmp_path / f"{SAMPLE_STEM}.md").exists()


def test_summarize_command_reports_an_over_length_transcript(tmp_path):
    long_transcript = tmp_path / "long_meeting.txt"
    long_transcript.write_text(
        "\n".join(f"[00:{second:02d}] Alex: {'launch checklist ' * 40}" for second in range(60)),
        encoding="utf-8",
    )

    # The real extract_meeting rejects this on its token budget, before any request.
    result = runner.invoke(
        main.app,
        [
            "summarize",
            str(long_transcript),
            "--title",
            "Sample Meeting",
            "--out",
            str(tmp_path),
            "--date",
            NOTE_DATE,
        ],
    )

    assert_reported_without_traceback(result, "Transcript is too long")
    assert "Chunking is not implemented" in result.output.replace("\n", "")
    assert not (tmp_path / f"{SAMPLE_STEM}.md").exists()


def test_preview_command_reports_a_non_txt_transcript(tmp_path):
    audio_path = tmp_path / "memo.m4a"
    audio_path.write_bytes(b"not really audio")

    result = runner.invoke(main.app, ["preview", str(audio_path)])

    assert_reported_without_traceback(result, "must point to a .txt file")


def test_transcribe_command_help_is_available():
    result = runner.invoke(main.app, ["transcribe", "--help"])

    assert result.exit_code == 0
    assert "Transcribe a local audio file" in result.output
    assert "--out" in result.output
    assert "--model" in result.output
    assert "<tiny|base|small|medium>" in result.output
    assert "[default: base]" in result.output
    assert "base is faster" in result.output
    assert "for testing" in result.output
    assert "small may improve quality" in result.output


def test_transcribe_command_rejects_unknown_model(tmp_path):
    result = runner.invoke(
        main.app,
        ["transcribe", "meeting.m4a", "--out", str(tmp_path), "--model", "large"],
    )

    assert result.exit_code == 2
    assert "large" in result.output


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


def test_summarize_command_generates_and_saves_note(
    monkeypatch, tmp_path, sample_transcript
):
    captured = {}

    def fake_extract_meeting(transcript, model):
        captured["transcript"] = transcript
        captured["model"] = model
        return make_extraction("Launch stays on track.")

    monkeypatch.setattr(main, "extract_meeting", fake_extract_meeting)

    result = runner.invoke(
        main.app,
        [
            "summarize",
            str(sample_transcript),
            "--title",
            "Sample Meeting",
            "--out",
            str(tmp_path),
            "--date",
            NOTE_DATE,
        ],
    )

    note_path = tmp_path / f"{SAMPLE_STEM}.md"

    assert result.exit_code == 0
    assert captured["model"] == "qwen2.5:7b"
    assert "Alex: Let's start with the launch checklist." in captured["transcript"]
    assert "\n\n" not in captured["transcript"]
    assert "## Summary" in result.output
    assert "Launch stays on track." in result.output
    assert f"{SAMPLE_STEM}.md" in result.output
    assert "No action items found; Action Items.md was not updated." in result.output
    saved_note = note_path.read_text(encoding="utf-8")
    assert saved_note.startswith("---\n")
    assert "type: meeting-note" in saved_note
    assert f"date: {NOTE_DATE}" in saved_note
    assert "source: transcript" in saved_note
    assert "model: qwen2.5:7b" in saved_note
    assert "tags:\n  - meeting-notes" in saved_note
    assert "# Meeting Notes: Sample Meeting" in saved_note
    assert "# Meeting Notes: Sample Meeting\n\n## Summary\n\nLaunch stays on track." in saved_note
    assert "## Meeting Health\n\n- Decisions made: 0" in saved_note
    assert saved_note.endswith("## Evidence / Timestamps\n\nNone explicitly mentioned.")
    assert "```" not in saved_note
    assert not (tmp_path / "Action Items.md").exists()


def test_summarize_command_defaults_date_to_today(
    monkeypatch, tmp_path, sample_transcript
):
    monkeypatch.setattr(
        main,
        "extract_meeting",
        lambda transcript, model: make_extraction("Dated today."),
    )

    result = runner.invoke(
        main.app,
        [
            "summarize",
            str(sample_transcript),
            "--title",
            "Sample Meeting",
            "--out",
            str(tmp_path),
        ],
    )

    today = date.today()
    note_path = tmp_path / f"{note_stem(today, 'Sample Meeting')}.md"

    assert result.exit_code == 0
    assert note_path.exists()
    assert f"date: {today.isoformat()}" in note_path.read_text(encoding="utf-8")


def test_summarize_command_rejects_invalid_date(
    monkeypatch, tmp_path, sample_transcript
):
    monkeypatch.setattr(main, "extract_meeting", fail_if_called)

    result = runner.invoke(
        main.app,
        [
            "summarize",
            str(sample_transcript),
            "--title",
            "Sample Meeting",
            "--out",
            str(tmp_path),
            "--date",
            "15-01-2026",
        ],
    )

    assert result.exit_code == 2
    assert "--date" in result.output
    assert list(tmp_path.glob("*.md")) == []


def test_summarize_command_transcribes_audio_input(
    monkeypatch, tmp_path, sample_audio
):
    captured = {}

    def fake_transcribe_audio(audio_path, model_size):
        captured["audio_path"] = str(audio_path)
        captured["model_size"] = model_size
        return [
            TranscriptSegment(0, "Alex: Let's start with the launch checklist."),
            TranscriptSegment(18, "Sam: I can own the QA pass by Friday."),
        ]

    monkeypatch.setattr(main, "transcribe_audio", fake_transcribe_audio)
    monkeypatch.setattr(
        main,
        "extract_meeting",
        lambda transcript, model: make_extraction(f"Heard: {transcript}"),
    )
    out = tmp_path / "Meetings"

    result = runner.invoke(
        main.app,
        [
            "summarize",
            str(sample_audio),
            "--title",
            "Sample Meeting",
            "--out",
            str(out),
            "--date",
            NOTE_DATE,
        ],
    )

    transcript_path = out / "transcripts" / f"{SAMPLE_STEM}.txt"
    note_path = out / f"{SAMPLE_STEM}.md"

    assert result.exit_code == 0
    assert captured["audio_path"] == str(sample_audio)
    assert captured["model_size"] == "base"
    assert transcript_path.read_text(encoding="utf-8") == (
        "[00:00] Alex: Let's start with the launch checklist.\n"
        "[00:18] Sam: I can own the QA pass by Friday."
    )
    assert "Saved transcript:" in result.output
    # Rich wraps long paths, so compare against the unwrapped output.
    assert f"{SAMPLE_STEM}.txt" in result.output.replace("\n", "")
    saved_note = note_path.read_text(encoding="utf-8")
    assert f"date: {NOTE_DATE}" in saved_note
    assert "source: audio" in saved_note
    assert "Alex: Let's start with the launch checklist." in saved_note


def test_summarize_command_passes_selected_whisper_model(
    monkeypatch, tmp_path, sample_audio
):
    captured = {}

    def fake_transcribe_audio(audio_path, model_size):
        captured["model_size"] = model_size
        return [TranscriptSegment(0, "A short memo.")]

    monkeypatch.setattr(main, "transcribe_audio", fake_transcribe_audio)
    monkeypatch.setattr(
        main,
        "extract_meeting",
        lambda transcript, model: make_extraction("Memo summarized."),
    )

    result = runner.invoke(
        main.app,
        [
            "summarize",
            str(sample_audio),
            "--title",
            "Sample Meeting",
            "--out",
            str(tmp_path),
            "--whisper-model",
            "small",
        ],
    )

    assert result.exit_code == 0
    assert captured["model_size"] == "small"


def test_summarize_command_refuses_to_overwrite_existing_note(
    monkeypatch, tmp_path, sample_audio
):
    monkeypatch.setattr(
        main,
        "extract_meeting",
        lambda transcript, model: make_extraction("First run.", [SEND_NOTES]),
    )
    monkeypatch.setattr(
        main,
        "transcribe_audio",
        lambda audio_path, model_size: [TranscriptSegment(0, "A short memo.")],
    )
    first_run = runner.invoke(
        main.app,
        [
            "summarize",
            str(sample_audio),
            "--title",
            "Sample Meeting",
            "--out",
            str(tmp_path),
            "--date",
            NOTE_DATE,
        ],
    )
    assert first_run.exit_code == 0

    note_path = tmp_path / f"{SAMPLE_STEM}.md"
    action_items_path = tmp_path / "Action Items.md"
    note_before = note_path.read_text(encoding="utf-8")
    action_items_before = action_items_path.read_text(encoding="utf-8")

    monkeypatch.setattr(main, "extract_meeting", fail_if_called)
    monkeypatch.setattr(main, "transcribe_audio", fail_if_called)

    second_run = runner.invoke(
        main.app,
        [
            "summarize",
            str(sample_audio),
            "--title",
            "Sample Meeting",
            "--out",
            str(tmp_path),
            "--date",
            NOTE_DATE,
        ],
    )

    assert second_run.exit_code == 1
    assert "Note already exists:" in second_run.output
    assert f"{SAMPLE_STEM}.md" in second_run.output
    assert "--force" in second_run.output
    assert note_path.read_text(encoding="utf-8") == note_before
    assert action_items_path.read_text(encoding="utf-8") == action_items_before


def test_summarize_command_force_rewrites_note_and_keeps_action_items(
    monkeypatch, tmp_path, sample_transcript
):
    monkeypatch.setattr(
        main,
        "extract_meeting",
        lambda transcript, model: make_extraction("First run.", [SEND_NOTES]),
    )
    args = [
        "summarize",
        str(sample_transcript),
        "--title",
        "Sample Meeting",
        "--out",
        str(tmp_path),
        "--date",
        NOTE_DATE,
    ]
    assert runner.invoke(main.app, args).exit_code == 0

    note_path = tmp_path / f"{SAMPLE_STEM}.md"
    action_items_path = tmp_path / "Action Items.md"
    checked_action_items = action_items_path.read_text(encoding="utf-8").replace(
        "- [ ]", "- [x]"
    )
    action_items_path.write_text(checked_action_items, encoding="utf-8")

    monkeypatch.setattr(
        main,
        "extract_meeting",
        lambda transcript, model: make_extraction("Second run.", [SEND_NOTES]),
    )

    result = runner.invoke(main.app, args + ["--force"])

    assert result.exit_code == 0
    assert "Second run." in note_path.read_text(encoding="utf-8")
    assert action_items_path.read_text(encoding="utf-8") == checked_action_items
    assert checked_action_items.count(f"## From [[{SAMPLE_STEM}]]") == 1
    assert f"Action items for [[{SAMPLE_STEM}]] already exist" in result.output


def test_summarize_command_separates_same_title_on_different_dates(
    monkeypatch, tmp_path, sample_transcript
):
    monkeypatch.setattr(
        main,
        "extract_meeting",
        lambda transcript, model: make_extraction("Launch planning happened.", [SEND_NOTES]),
    )

    def run(note_date, *extra):
        return runner.invoke(
            main.app,
            [
                "summarize",
                str(sample_transcript),
                "--title",
                "Sample Meeting",
                "--out",
                str(tmp_path),
                "--date",
                note_date,
                *extra,
            ],
        )

    assert run("2026-01-15").exit_code == 0
    second_run = run("2026-02-01", "--link-related")

    january_stem = "2026-01-15-sample-meeting"
    february_stem = "2026-02-01-sample-meeting"
    action_items_content = (tmp_path / "Action Items.md").read_text(encoding="utf-8")

    assert second_run.exit_code == 0
    assert (tmp_path / f"{january_stem}.md").exists()
    assert (tmp_path / f"{february_stem}.md").exists()
    assert f"## From [[{january_stem}]]" in action_items_content
    assert f"## From [[{february_stem}]]" in action_items_content

    february_note = (tmp_path / f"{february_stem}.md").read_text(encoding="utf-8")
    assert f"[[{january_stem}]]" in february_note


def test_summarize_command_does_not_link_a_note_to_itself_on_force_rerun(
    monkeypatch, tmp_path, sample_transcript
):
    monkeypatch.setattr(
        main,
        "extract_meeting",
        lambda transcript, model: make_extraction("Launch QA stayed on track."),
    )
    args = [
        "summarize",
        str(sample_transcript),
        "--title",
        "Sample Meeting",
        "--out",
        str(tmp_path),
        "--date",
        NOTE_DATE,
        "--link-related",
    ]
    assert runner.invoke(main.app, args).exit_code == 0

    result = runner.invoke(main.app, args + ["--force"])

    saved_note = (tmp_path / f"{SAMPLE_STEM}.md").read_text(encoding="utf-8")

    assert result.exit_code == 0
    assert "No related meetings found." in result.output
    assert f"[[{SAMPLE_STEM}]]" not in saved_note
    assert "## Related Meetings" not in saved_note


def test_summarize_command_passes_selected_model(
    monkeypatch, tmp_path, sample_transcript
):
    captured = {}

    def fake_extract_meeting(transcript, model):
        captured["model"] = model
        return make_extraction("Custom model used.")

    monkeypatch.setattr(main, "extract_meeting", fake_extract_meeting)

    result = runner.invoke(
        main.app,
        [
            "summarize",
            str(sample_transcript),
            "--title",
            "Sample Meeting",
            "--out",
            str(tmp_path),
            "--date",
            NOTE_DATE,
            "--model",
            "test-model",
        ],
    )

    assert result.exit_code == 0
    assert captured["model"] == "test-model"
    saved_note = (tmp_path / f"{SAMPLE_STEM}.md").read_text(encoding="utf-8")
    assert "model: test-model" in saved_note


def test_summarize_command_uses_out_as_output_folder(
    monkeypatch, tmp_path, sample_transcript
):
    monkeypatch.setattr(
        main,
        "extract_meeting",
        lambda transcript, model: make_extraction("Saved to nested folder."),
    )
    out = tmp_path / "nested" / "meetings"

    result = runner.invoke(
        main.app,
        [
            "summarize",
            str(sample_transcript),
            "--title",
            "Nested Meeting",
            "--out",
            str(out),
            "--date",
            NOTE_DATE,
        ],
    )

    assert result.exit_code == 0
    assert (out / Path(f"{NOTE_DATE}-nested-meeting.md")).exists()


def test_summarize_command_appends_action_items(
    monkeypatch, tmp_path, sample_transcript
):
    monkeypatch.setattr(
        main,
        "extract_meeting",
        lambda transcript, model: make_extraction("Launch planning happened.", [SEND_NOTES]),
    )

    result = runner.invoke(
        main.app,
        [
            "summarize",
            str(sample_transcript),
            "--title",
            "Sample Meeting",
            "--out",
            str(tmp_path),
            "--date",
            NOTE_DATE,
        ],
    )

    note_path = tmp_path / f"{SAMPLE_STEM}.md"
    action_items_path = tmp_path / "Action Items.md"

    assert result.exit_code == 0
    assert note_path.exists()
    assert action_items_path.exists()
    assert f"{SAMPLE_STEM}.md" in result.output
    assert "Updated action items:" in result.output
    assert "Action Items.md" in result.output

    action_items_content = action_items_path.read_text(encoding="utf-8")
    assert f"## From [[{SAMPLE_STEM}]]" in action_items_content
    assert "- [ ] Send launch notes — Owner: Avi — Due: Friday" in action_items_content
    assert f"  - Source: [[{SAMPLE_STEM}]]" in action_items_content
    assert "[[Sample Meeting]]" not in action_items_content

    saved_note = note_path.read_text(encoding="utf-8")
    assert "# Meeting Notes: Sample Meeting" in saved_note
    assert "- [ ] Send launch notes — Owner: Avi — Due: Friday" in saved_note
    assert "- Action items created: 1" in saved_note


def test_summarize_command_does_not_create_action_items_when_none_found(
    monkeypatch,
    tmp_path,
    sample_transcript,
):
    monkeypatch.setattr(
        main,
        "extract_meeting",
        lambda transcript, model: make_extraction("No action items today."),
    )

    result = runner.invoke(
        main.app,
        [
            "summarize",
            str(sample_transcript),
            "--title",
            "Sample Meeting",
            "--out",
            str(tmp_path),
            "--date",
            NOTE_DATE,
        ],
    )

    assert result.exit_code == 0
    assert (tmp_path / f"{SAMPLE_STEM}.md").exists()
    assert not (tmp_path / "Action Items.md").exists()
    assert f"{SAMPLE_STEM}.md" in result.output
    assert "No action items found; Action Items.md was not updated." in result.output


def test_summarize_command_does_not_load_related_notes_without_flag(
    monkeypatch,
    tmp_path,
    sample_transcript,
):
    monkeypatch.setattr(
        main,
        "extract_meeting",
        lambda transcript, model: make_extraction("Launch stays on track."),
    )
    monkeypatch.setattr(main, "load_meeting_notes", fail_if_called)

    result = runner.invoke(
        main.app,
        [
            "summarize",
            str(sample_transcript),
            "--title",
            "Sample Meeting",
            "--out",
            str(tmp_path),
            "--date",
            NOTE_DATE,
        ],
    )

    assert result.exit_code == 0
    assert "No related meetings found." not in result.output


def test_summarize_command_link_related_adds_related_meetings_section(
    monkeypatch,
    tmp_path,
    sample_transcript,
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
        "extract_meeting",
        lambda transcript, model: make_extraction("Launch QA stayed on track."),
    )

    result = runner.invoke(
        main.app,
        [
            "summarize",
            str(sample_transcript),
            "--title",
            "Sample Meeting",
            "--out",
            str(tmp_path),
            "--date",
            NOTE_DATE,
            "--link-related",
        ],
    )

    saved_note = (tmp_path / f"{SAMPLE_STEM}.md").read_text(encoding="utf-8")

    assert result.exit_code == 0
    assert "Added related meetings: 1" in result.output
    assert "## Related Meetings" in saved_note
    assert "[[sample-retro]]" in saved_note


def test_summarize_command_link_related_with_no_matches_adds_no_empty_section(
    monkeypatch,
    tmp_path,
    sample_transcript,
):
    previous_note = tmp_path / "budget-review.md"
    previous_note.write_text(
        "# Budget Review\n\n## Summary\n\nDiscussed finance forecasts.",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        main,
        "extract_meeting",
        lambda transcript, model: make_extraction("Launch QA stayed on track."),
    )

    result = runner.invoke(
        main.app,
        [
            "summarize",
            str(sample_transcript),
            "--title",
            "Sample Meeting",
            "--out",
            str(tmp_path),
            "--date",
            NOTE_DATE,
            "--link-related",
        ],
    )

    saved_note = (tmp_path / f"{SAMPLE_STEM}.md").read_text(encoding="utf-8")

    assert result.exit_code == 0
    assert "No related meetings found." in result.output
    assert "## Related Meetings" not in saved_note


def test_summarize_command_appends_action_items_when_related_meetings_are_added(
    monkeypatch,
    tmp_path,
    sample_transcript,
):
    (tmp_path / "sample-retro.md").write_text(
        "# Sample Retro\n\n## Summary\n\nDiscussed launch QA.",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        main,
        "extract_meeting",
        lambda transcript, model: make_extraction("Launch QA stayed on track.", [SEND_NOTES]),
    )

    result = runner.invoke(
        main.app,
        [
            "summarize",
            str(sample_transcript),
            "--title",
            "Sample Meeting",
            "--out",
            str(tmp_path),
            "--date",
            NOTE_DATE,
            "--link-related",
        ],
    )

    saved_note = (tmp_path / f"{SAMPLE_STEM}.md").read_text(encoding="utf-8")
    action_items_content = (tmp_path / "Action Items.md").read_text(encoding="utf-8")

    assert result.exit_code == 0
    assert "## Related Meetings" in saved_note
    assert "- [ ] Send launch notes" in action_items_content
    assert f"  - Source: [[{SAMPLE_STEM}]]" in action_items_content


DEBRIEF_STEM = f"{NOTE_DATE}-northwind-debrief"
SEND_PORTFOLIO = ActionItem(task="Send portfolio link", owner="Me", due="Friday, October 3rd")
PRIYA_REPLY = ActionItem(task="Get back about the next round", owner="Priya Raman", due="within a week")


def make_debrief(commitments=()):
    return DebriefExtraction(
        summary="First technical round went well.",
        questions_asked=["Write a 7-day retention query"],
        weak_spots=["Window functions"],
        people_mentioned=[Person(name="Priya Raman", role="Analytics manager")],
        commitments=list(commitments),
        open_questions=["Salary range"],
    )


def run_debrief(tmp_path, transcript_path, *extra_args):
    return runner.invoke(
        main.app,
        [
            "summarize",
            str(transcript_path),
            "--mode",
            "debrief",
            "--out",
            str(tmp_path),
            "--date",
            NOTE_DATE,
            *extra_args,
        ],
    )


def test_summarize_debrief_writes_note_with_six_sections_and_company(
    monkeypatch, tmp_path, sample_transcript
):
    monkeypatch.setattr(main, "extract_meeting", fail_if_called)
    monkeypatch.setattr(
        main, "extract_debrief", lambda transcript, model: make_debrief([SEND_PORTFOLIO])
    )

    result = run_debrief(tmp_path, sample_transcript, "--company", "Northwind")

    assert result.exit_code == 0, result.output
    saved_note = (tmp_path / f"{DEBRIEF_STEM}.md").read_text(encoding="utf-8")
    assert saved_note.startswith("---\ntype: debrief\n")
    assert f"date: {NOTE_DATE}" in saved_note
    assert "company: Northwind\n" in saved_note
    assert "tags:\n  - debrief" in saved_note
    assert "# Debrief: Northwind debrief\n\n## Summary" in saved_note
    for heading in [
        "## Summary",
        "## Questions Asked",
        "## Weak Spots to Prep",
        "## People Mentioned",
        "## Commitments",
        "## Open Questions",
    ]:
        assert heading in saved_note
    assert "## Meeting Health" not in saved_note
    assert "- [ ] Send portfolio link — Owner: Me — Due: Friday, October 3rd" in saved_note


def test_summarize_debrief_uses_explicit_title(monkeypatch, tmp_path, sample_transcript):
    monkeypatch.setattr(main, "extract_debrief", lambda transcript, model: make_debrief())

    result = run_debrief(
        tmp_path, sample_transcript, "--company", "Northwind", "--title", "Round One"
    )

    assert result.exit_code == 0, result.output
    saved_note = (tmp_path / f"{NOTE_DATE}-round-one.md").read_text(encoding="utf-8")
    assert "# Debrief: Round One" in saved_note
    assert "company: Northwind" in saved_note


def test_summarize_debrief_without_company_fails_clearly(
    monkeypatch, tmp_path, sample_transcript
):
    monkeypatch.setattr(main, "extract_debrief", fail_if_called)

    result = run_debrief(tmp_path, sample_transcript, "--title", "Round One")

    assert result.exit_code == 1
    assert "--company is required with --mode debrief." in result.output
    assert list(tmp_path.glob("*.md")) == []


def test_summarize_meeting_without_title_fails_clearly(
    monkeypatch, tmp_path, sample_transcript
):
    monkeypatch.setattr(main, "extract_meeting", fail_if_called)

    result = runner.invoke(
        main.app, ["summarize", str(sample_transcript), "--out", str(tmp_path)]
    )

    assert result.exit_code == 1
    assert "--title is required in meeting mode." in result.output
    assert list(tmp_path.glob("*.md")) == []


def test_summarize_meeting_rejects_company(monkeypatch, tmp_path, sample_transcript):
    monkeypatch.setattr(main, "extract_meeting", fail_if_called)

    result = runner.invoke(
        main.app,
        [
            "summarize",
            str(sample_transcript),
            "--title",
            "Sample Meeting",
            "--company",
            "Northwind",
            "--out",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 1
    assert "--company is only used with --mode debrief." in result.output
    assert list(tmp_path.glob("*.md")) == []


def test_summarize_debrief_appends_commitments_once_after_rerun(
    monkeypatch, tmp_path, sample_transcript
):
    monkeypatch.setattr(
        main,
        "extract_debrief",
        lambda transcript, model: make_debrief([SEND_PORTFOLIO, PRIYA_REPLY]),
    )

    first = run_debrief(tmp_path, sample_transcript, "--company", "Northwind")
    second = run_debrief(tmp_path, sample_transcript, "--company", "Northwind", "--force")

    assert first.exit_code == 0, first.output
    assert second.exit_code == 0, second.output
    action_items = (tmp_path / "Action Items.md").read_text(encoding="utf-8")
    assert action_items.count(f"## From [[{DEBRIEF_STEM}]]") == 1
    assert action_items.count("Send portfolio link") == 1
    assert "- [ ] Get back about the next round — Owner: Priya Raman — Due: within a week" in action_items
    assert f"  - Source: [[{DEBRIEF_STEM}]]" in action_items
    assert f"Action items for [[{DEBRIEF_STEM}]] already exist" in second.output
