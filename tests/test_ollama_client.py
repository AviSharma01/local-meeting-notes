import json

import pytest
import requests

from src.models import MeetingExtraction
from src.ollama_client import (
    DEFAULT_MODEL,
    NUM_CTX,
    REQUEST_TIMEOUT_SECONDS,
    extract_meeting,
    ollama_base_url,
)


VALID_EXTRACTION = {
    "summary": "Launch date stays.",
    "decisions": [{"text": "Keep the launch date", "evidence": "[00:12]"}],
    "action_items": [],
    "follow_ups": [],
    "risks": [],
    "open_questions": [],
    "needs_review": [],
}


class FakeResponse:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        return None

    def json(self):
        return self.data


def fake_post_returning(*texts):
    """Return a fake requests.post that replies with each text in turn and records calls."""
    calls = []
    remaining = list(texts)

    def fake_post(url, json, timeout):
        calls.append({"url": url, "json": json, "timeout": timeout})
        return FakeResponse({"response": remaining.pop(0)})

    return fake_post, calls


@pytest.fixture(autouse=True)
def clear_ollama_host(monkeypatch):
    monkeypatch.delenv("OLLAMA_HOST", raising=False)


def test_extract_meeting_sends_json_request_to_local_ollama(monkeypatch):
    fake_post, calls = fake_post_returning(json.dumps(VALID_EXTRACTION))
    monkeypatch.setattr(requests, "post", fake_post)

    extract_meeting("[00:12] Avi: Let's keep the launch date.")

    assert len(calls) == 1
    assert calls[0]["url"] == "http://localhost:11434/api/generate"
    assert calls[0]["json"]["model"] == DEFAULT_MODEL == "qwen2.5:7b"
    assert calls[0]["json"]["stream"] is False
    assert calls[0]["json"]["format"] == "json"
    assert calls[0]["json"]["options"] == {"num_ctx": 8192}
    assert NUM_CTX == 8192
    assert calls[0]["timeout"] == REQUEST_TIMEOUT_SECONDS == 300


def test_extract_meeting_passes_selected_model(monkeypatch):
    fake_post, calls = fake_post_returning(json.dumps(VALID_EXTRACTION))
    monkeypatch.setattr(requests, "post", fake_post)

    extract_meeting("Avi: Hello", model="test-model")

    assert calls[0]["json"]["model"] == "test-model"


def test_extract_meeting_includes_transcript_in_prompt(monkeypatch):
    transcript = "Avi: This exact transcript text should be included."
    fake_post, calls = fake_post_returning(json.dumps(VALID_EXTRACTION))
    monkeypatch.setattr(requests, "post", fake_post)

    extract_meeting(transcript)

    assert transcript in calls[0]["json"]["prompt"]
    assert "{{ transcript }}" not in calls[0]["json"]["prompt"]


def test_extract_meeting_returns_validated_extraction(monkeypatch):
    fake_post, _ = fake_post_returning(json.dumps(VALID_EXTRACTION))
    monkeypatch.setattr(requests, "post", fake_post)

    extraction = extract_meeting("Avi: We discussed launch planning.")

    assert extraction == MeetingExtraction.model_validate(VALID_EXTRACTION)


def test_extract_meeting_retries_once_with_error_after_malformed_json(monkeypatch):
    fake_post, calls = fake_post_returning("{not json", json.dumps(VALID_EXTRACTION))
    monkeypatch.setattr(requests, "post", fake_post)

    extraction = extract_meeting("Avi: Hello")

    assert len(calls) == 2
    first_prompt = calls[0]["json"]["prompt"]
    retry_prompt = calls[1]["json"]["prompt"]
    assert retry_prompt.startswith(first_prompt)
    assert "Your previous response was invalid" in retry_prompt
    assert "Invalid JSON" in retry_prompt
    assert extraction.summary == "Launch date stays."


def test_extract_meeting_malformed_json_twice_raises_clear_error(monkeypatch):
    fake_post, calls = fake_post_returning("{not json", "still not json")
    monkeypatch.setattr(requests, "post", fake_post)

    with pytest.raises(RuntimeError, match="invalid meeting JSON after one retry"):
        extract_meeting("Avi: Hello")

    assert len(calls) == 2


def test_extract_meeting_schema_mismatch_twice_raises_clear_error(monkeypatch):
    fake_post, calls = fake_post_returning(
        json.dumps({"summary": "Missing lists."}),
        json.dumps({"summary": "Still missing lists."}),
    )
    monkeypatch.setattr(requests, "post", fake_post)

    with pytest.raises(RuntimeError, match="invalid meeting JSON after one retry"):
        extract_meeting("Avi: Hello")

    assert len(calls) == 2
    assert "decisions" in calls[1]["json"]["prompt"].split("Your previous response was invalid")[1]


def test_extract_meeting_over_budget_transcript_raises_without_calling_ollama(monkeypatch):
    def fail_if_called(url, json, timeout):
        raise AssertionError("Ollama should not be called")

    monkeypatch.setattr(requests, "post", fail_if_called)
    transcript = "Avi: word " * 4000

    with pytest.raises(ValueError, match="Transcript is too long.*Chunking is not implemented"):
        extract_meeting(transcript)


def test_extract_meeting_failed_request_raises_clear_error(monkeypatch):
    def fake_post(url, json, timeout):
        raise requests.RequestException("connection refused")

    monkeypatch.setattr(requests, "post", fake_post)

    with pytest.raises(RuntimeError, match="Ollama request failed"):
        extract_meeting("Avi: Hello")


def test_extract_meeting_missing_response_raises_clear_error(monkeypatch):
    def fake_post(url, json, timeout):
        return FakeResponse({"done": True})

    monkeypatch.setattr(requests, "post", fake_post)

    with pytest.raises(RuntimeError, match="Ollama returned an invalid response"):
        extract_meeting("Avi: Hello")


def test_extract_meeting_empty_transcript_raises_value_error():
    with pytest.raises(ValueError, match="Transcript cannot be empty."):
        extract_meeting("")

    with pytest.raises(ValueError, match="Transcript cannot be empty."):
        extract_meeting(" \n\t ")


def test_extract_meeting_uses_ollama_host_from_environment(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "http://127.0.0.1:9999")
    fake_post, calls = fake_post_returning(json.dumps(VALID_EXTRACTION))
    monkeypatch.setattr(requests, "post", fake_post)

    extract_meeting("Avi: Hello")

    assert calls[0]["url"] == "http://127.0.0.1:9999/api/generate"


@pytest.mark.parametrize(
    ("host", "expected"),
    [
        ("localhost:11434", "http://localhost:11434"),
        ("127.0.0.1:11434", "http://127.0.0.1:11434"),
        ("[::1]:11434", "http://[::1]:11434"),
        ("http://localhost:11434/", "http://localhost:11434"),
        ("", "http://localhost:11434"),
    ],
)
def test_ollama_base_url_accepts_loopback_hosts(monkeypatch, host, expected):
    monkeypatch.setenv("OLLAMA_HOST", host)

    assert ollama_base_url() == expected


@pytest.mark.parametrize(
    ("host", "expected"),
    [
        ("localhost", "http://localhost:11434"),
        ("127.0.0.1", "http://127.0.0.1:11434"),
        ("[::1]", "http://[::1]:11434"),
        ("http://localhost", "http://localhost:11434"),
        ("http://localhost/", "http://localhost:11434"),
    ],
)
def test_ollama_base_url_defaults_port_to_11434(monkeypatch, host, expected):
    monkeypatch.setenv("OLLAMA_HOST", host)

    assert ollama_base_url() == expected


@pytest.mark.parametrize(
    "host",
    [
        "http://example.com:11434",
        "192.168.1.20:11434",
        "0.0.0.0:11434",
        "http://localhost.example.com",
        "http://127.0.0.1@example.com",
    ],
)
def test_ollama_base_url_rejects_non_loopback_hosts(monkeypatch, host):
    monkeypatch.setenv("OLLAMA_HOST", host)

    with pytest.raises(ValueError, match="OLLAMA_HOST must point to this machine"):
        ollama_base_url()


def test_extract_meeting_rejects_remote_host_without_calling_ollama(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "http://example.com:11434")

    def fail_if_called(url, json, timeout):
        raise AssertionError("Ollama should not be called")

    monkeypatch.setattr(requests, "post", fail_if_called)

    with pytest.raises(ValueError, match="OLLAMA_HOST must point to this machine"):
        extract_meeting("Avi: Hello")
