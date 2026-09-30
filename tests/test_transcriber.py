import sys
import types

import pytest

import src.transcriber as transcriber
from src.transcriber import (
    TranscriptSegment,
    format_timestamp,
    format_transcript,
    transcript_filename,
    transcribe_audio,
    write_transcript,
)


class FakeWhisperSegment:
    def __init__(self, start, text):
        self.start = start
        self.text = text


def fail_if_called(*args, **kwargs):
    raise AssertionError("This should not have been called")


@pytest.fixture
def audio_file(tmp_path):
    path = tmp_path / "meeting.m4a"
    path.write_bytes(b"not really audio")
    return path


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


def test_write_transcript_uses_a_given_stem_instead_of_the_audio_name(tmp_path):
    segments = [TranscriptSegment(0, "First transcribed segment.")]

    transcript_path = write_transcript(
        tmp_path,
        "Meeting.m4a",
        segments,
        stem="2026-01-15-sample-meeting",
    )

    assert transcript_path == tmp_path / "2026-01-15-sample-meeting.txt"
    assert transcript_path.read_text(encoding="utf-8") == (
        "[00:00] First transcribed segment."
    )


def test_transcribe_audio_converts_faster_whisper_segments(monkeypatch, audio_file):
    captured = {}

    class FakeWhisperModel:
        def transcribe(self, audio_path):
            captured["audio_path"] = audio_path
            return [
                FakeWhisperSegment(0.0, " First transcribed segment. "),
                FakeWhisperSegment(18.5, "Second transcribed segment."),
            ], object()

    def fake_create_whisper_model(model_size):
        captured["model_size"] = model_size
        return FakeWhisperModel()

    monkeypatch.setattr(transcriber, "_create_whisper_model", fake_create_whisper_model)

    segments = transcribe_audio(audio_file)

    assert captured == {"model_size": "small", "audio_path": str(audio_file)}
    assert segments == [
        TranscriptSegment(start_seconds=0.0, text="First transcribed segment."),
        TranscriptSegment(start_seconds=18.5, text="Second transcribed segment."),
    ]


def test_transcribe_audio_skips_blank_segments(monkeypatch, audio_file):
    class FakeWhisperModel:
        def transcribe(self, audio_path):
            return [
                FakeWhisperSegment(0.0, "First transcribed segment."),
                FakeWhisperSegment(18.0, "   "),
            ], object()

    monkeypatch.setattr(
        transcriber,
        "_create_whisper_model",
        lambda model_size: FakeWhisperModel(),
    )

    assert transcribe_audio(audio_file) == [
        TranscriptSegment(start_seconds=0.0, text="First transcribed segment.")
    ]


def test_transcribe_audio_uses_selected_model_size(monkeypatch, audio_file):
    captured = {}

    class FakeWhisperModel:
        def transcribe(self, audio_path):
            return [], object()

    def fake_create_whisper_model(model_size):
        captured["model_size"] = model_size
        return FakeWhisperModel()

    monkeypatch.setattr(transcriber, "_create_whisper_model", fake_create_whisper_model)

    assert transcribe_audio(audio_file, model_size="medium") == []
    assert captured["model_size"] == "medium"


def test_transcribe_audio_missing_file_is_reported_before_loading_a_model(monkeypatch):
    monkeypatch.setattr(transcriber, "_create_whisper_model", fail_if_called)

    with pytest.raises(RuntimeError) as exc_info:
        transcribe_audio("missing.m4a")

    assert str(exc_info.value) == "Audio file not found: 'missing.m4a'."


def test_transcribe_audio_reports_other_failures_with_the_original_message(
    monkeypatch, audio_file
):
    class FakeWhisperModel:
        def transcribe(self, audio_path):
            raise ValueError("decode failed")

    monkeypatch.setattr(
        transcriber,
        "_create_whisper_model",
        lambda model_size: FakeWhisperModel(),
    )

    with pytest.raises(RuntimeError) as exc_info:
        transcribe_audio(audio_file)

    message = str(exc_info.value)
    assert f"Could not transcribe audio file '{audio_file}'" in message
    assert "decode failed" in message


def test_create_whisper_model_uses_cpu_int8_and_local_files_only(monkeypatch):
    captured = {}

    class FakeWhisperModel:
        def __init__(self, model_size, **kwargs):
            captured["model_size"] = model_size
            captured.update(kwargs)

    fake_module = types.ModuleType("faster_whisper")
    fake_module.WhisperModel = FakeWhisperModel
    monkeypatch.setitem(sys.modules, "faster_whisper", fake_module)

    model = transcriber._create_whisper_model("small")

    assert isinstance(model, FakeWhisperModel)
    assert captured == {
        "model_size": "small",
        "device": "cpu",
        "compute_type": "int8",
        "local_files_only": True,
    }


def test_create_whisper_model_missing_model_gives_download_command(monkeypatch):
    class FakeWhisperModel:
        def __init__(self, model_size, **kwargs):
            raise FileNotFoundError("no cached snapshot")

    fake_module = types.ModuleType("faster_whisper")
    fake_module.WhisperModel = FakeWhisperModel
    monkeypatch.setitem(sys.modules, "faster_whisper", fake_module)

    with pytest.raises(RuntimeError) as exc_info:
        transcriber._create_whisper_model("small")

    message = str(exc_info.value)
    assert "Whisper model 'small' is not downloaded" in message
    assert "download_model('small')" in message


def test_create_whisper_model_missing_dependency_raises_helpful_error(monkeypatch):
    original_import = __import__

    def fake_import(name, *args, **kwargs):
        if name == "faster_whisper":
            raise ImportError("missing faster-whisper")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)

    with pytest.raises(RuntimeError) as exc_info:
        transcriber._create_whisper_model("base")

    message = str(exc_info.value)
    assert "faster-whisper is not installed" in message
    assert "pip install -r requirements.txt" in message
