import pytest
import requests

from src.ollama_client import OLLAMA_GENERATE_URL, generate_meeting_notes


class FakeResponse:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        return None

    def json(self):
        return self.data


def test_generate_meeting_notes_sends_request_to_local_ollama(monkeypatch):
    transcript = "[00:12] Avi: Let's keep the launch date."
    captured = {}

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return FakeResponse({"response": "# Summary\n\nLaunch date stays."})

    monkeypatch.setattr(requests, "post", fake_post)

    generate_meeting_notes(transcript)

    assert captured["url"] == OLLAMA_GENERATE_URL
    assert captured["json"]["model"] == "qwen2.5:7b"
    assert captured["json"]["stream"] is False
    assert captured["timeout"] == 60


def test_generate_meeting_notes_includes_transcript_in_prompt(monkeypatch):
    transcript = "Avi: This exact transcript text should be included."
    captured = {}

    def fake_post(url, json, timeout):
        captured["prompt"] = json["prompt"]
        return FakeResponse({"response": "# Summary\n\nIncluded."})

    monkeypatch.setattr(requests, "post", fake_post)

    generate_meeting_notes(transcript)

    assert transcript in captured["prompt"]


def test_generate_meeting_notes_returns_response_text(monkeypatch):
    expected_text = "# Summary\n\nThe meeting covered launch planning."

    def fake_post(url, json, timeout):
        return FakeResponse({"response": expected_text})

    monkeypatch.setattr(requests, "post", fake_post)

    assert generate_meeting_notes("Avi: We discussed launch planning.") == expected_text


def test_generate_meeting_notes_failed_request_raises_clear_error(monkeypatch):
    def fake_post(url, json, timeout):
        raise requests.RequestException("connection refused")

    monkeypatch.setattr(requests, "post", fake_post)

    with pytest.raises(RuntimeError, match="Ollama request failed"):
        generate_meeting_notes("Avi: Hello")


def test_generate_meeting_notes_missing_response_raises_clear_error(monkeypatch):
    def fake_post(url, json, timeout):
        return FakeResponse({"done": True})

    monkeypatch.setattr(requests, "post", fake_post)

    with pytest.raises(RuntimeError, match="Ollama returned an invalid response"):
        generate_meeting_notes("Avi: Hello")


def test_generate_meeting_notes_empty_transcript_raises_value_error():
    with pytest.raises(ValueError, match="Transcript cannot be empty."):
        generate_meeting_notes("")

    with pytest.raises(ValueError, match="Transcript cannot be empty."):
        generate_meeting_notes(" \n\t ")
