import pytest

from src.transcriber import (
    TranscriptSegment,
    format_timestamp,
    format_transcript,
    transcript_filename,
    transcribe_audio,
    write_transcript,
)


def test_format_timestamp_uses_minutes_and_seconds():
    assert format_timestamp(0) == "[00:00]"
    assert format_timestamp(18) == "[00:18]"
    assert format_timestamp(65) == "[01:05]"


def test_format_timestamp_uses_hours_when_needed():
    assert format_timestamp(3661) == "[01:01:01]"


def test_format_transcript_formats_timestamped_segments():
    segments = [
        TranscriptSegment(0, "First transcribed segment."),
        TranscriptSegment(18, "Second transcribed segment."),
        TranscriptSegment(65, "Third transcribed segment."),
    ]

    assert format_transcript(segments) == (
        "[00:00] First transcribed segment.\n"
        "[00:18] Second transcribed segment.\n"
        "[01:05] Third transcribed segment."
    )


def test_format_transcript_skips_blank_segment_text():
    segments = [
        TranscriptSegment(0, "First transcribed segment."),
        TranscriptSegment(18, "   "),
    ]

    assert format_transcript(segments) == "[00:00] First transcribed segment."


def test_transcript_filename_uses_safe_audio_stem():
    assert transcript_filename("Team Sync: QA?.m4a") == "team-sync-qa.txt"


def test_write_transcript_creates_output_folder_and_writes_file(tmp_path):
    out = tmp_path / "nested" / "transcripts"
    segments = [
        TranscriptSegment(0, "First transcribed segment."),
        TranscriptSegment(18, "Second transcribed segment."),
    ]

    transcript_path = write_transcript(out, "Meeting.m4a", segments)

    assert transcript_path == out / "meeting.txt"
    assert transcript_path.read_text(encoding="utf-8") == (
        "[00:00] First transcribed segment.\n"
        "[00:18] Second transcribed segment."
    )


def test_transcribe_audio_placeholder_raises_helpful_error():
    with pytest.raises(RuntimeError, match="Local transcription is not configured yet"):
        transcribe_audio("meeting.m4a")
