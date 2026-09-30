import json
from datetime import date

import pytest
import requests

from evals import run
from evals.run import CaseResult, FieldScore
from src import ollama_client
from src.models import ActionItem, DebriefExtraction, Person


DEBRIEF_EXPECTED = {
    "mode": "debrief",
    "commitments": [
        {"keywords": ["portfolio"], "owner": "Me"},
        {"keywords": ["week"], "owner": "Priya"},
    ],
    "questions_asked": [
        {"keywords": ["retention", "cohort"]},
        {"keywords": ["drop", "active users"]},
    ],
    "people_mentioned": [
        {"keywords": ["priya"]},
        {"keywords": ["tom"]},
        {"keywords": ["sam"]},
    ],
}

MEETING_EXPECTED = {
    "mode": "meeting",
    "action_items": [{"keywords": ["runbook"]}],
    "decisions": [],
}

VALID_MEETING = {"summary": "Sync.", "action_items": [{"task": "Update the runbook"}]}


@pytest.fixture(autouse=True)
def clear_ollama_host(monkeypatch):
    monkeypatch.delenv("OLLAMA_HOST", raising=False)


def fail_if_called(*args, **kwargs):
    raise AssertionError("Ollama should not be called")


def fake_post_returning(*texts):
    remaining = list(texts)

    class FakeResponse:
        def __init__(self, text):
            self.text = text

        def raise_for_status(self):
            return None

        def json(self):
            return {"response": self.text}

    return lambda url, json, timeout: FakeResponse(remaining.pop(0))


def write_case(folder, expected):
    folder.mkdir()
    (folder / "transcript.txt").write_text("[00:50] Rosa: Someone update the runbook.")
    (folder / "expected.json").write_text(json.dumps(expected))
    return folder


def test_score_case_scores_a_fixed_extraction_against_expected_json(tmp_path, monkeypatch):
    monkeypatch.setattr(ollama_client.SESSION, "post", fail_if_called)
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    (case_dir / "expected.json").write_text(json.dumps(DEBRIEF_EXPECTED))
    extraction = DebriefExtraction(
        summary="First technical round.",
        commitments=[
            ActionItem(task="Send portfolio link", owner="Me", due="Friday"),
            ActionItem(task="Get back about the next round", owner="Priya Raman", due="within a week"),
            ActionItem(task="Practice window functions", owner="Me"),
        ],
        questions_asked=["Write a seven-day retention query by sign-up cohort"],
        people_mentioned=[
            Person(name="Priya Raman", role="Analytics manager"),
            Person(name="Tom"),
        ],
    )

    scores = run.score_case(run.load_expected(case_dir), extraction)

    assert scores == {
        "commitments": FieldScore(matched=2, expected=2, extracted=3),
        "questions_asked": FieldScore(matched=1, expected=2, extracted=1),
        "people_mentioned": FieldScore(matched=2, expected=3, extracted=2),
    }


@pytest.mark.parametrize(
    ("expected_owner", "extracted_owner", "matches"),
    [
        ("Priya", "Priya Raman", True),
        ("Me", "Me", True),
        ("me", "ME", True),
        ("Me", "Megan Cho", False),
        ("Pri", "Priya", False),
        ("Priya", None, False),
    ],
)
def test_owner_matches_equal_or_whole_word_ignoring_case(
    expected_owner, extracted_owner, matches
):
    assert run.owner_matches(expected_owner, extracted_owner) is matches


def test_each_extracted_item_matches_at_most_one_expected_item():
    expected_items = [{"keywords": ["portfolio"]}, {"keywords": ["portfolio"]}]

    assert run.count_matches(expected_items, ["Send portfolio link"]) == 1


def test_keywords_check_due_but_not_evidence():
    expected = {"keywords": ["intro", "next week"]}

    assert run.item_matches(
        expected, ActionItem(task="Introduce me to Farah", due="early next week")
    )
    assert not run.item_matches(
        expected, ActionItem(task="Introduce me to Farah", evidence="next week")
    )


def test_failed_extraction_scores_nothing_extracted():
    assert run.score_case(MEETING_EXPECTED, None) == {
        "action_items": FieldScore(matched=0, expected=1, extracted=0),
        "decisions": FieldScore(matched=0, expected=0, extracted=0),
    }


def test_run_case_reports_a_retry(tmp_path, monkeypatch):
    monkeypatch.setattr(
        ollama_client.SESSION, "post", fake_post_returning("{not json", json.dumps(VALID_MEETING))
    )
    case_dir = write_case(tmp_path / "sync", MEETING_EXPECTED)

    result = run.run_case(case_dir, "test-model", private=False)

    assert result.retried is True
    assert result.failed is False
    assert result.scores["action_items"] == FieldScore(matched=1, expected=1, extracted=1)
    assert run.ollama_client._generate is ollama_client._generate


def test_run_case_marks_invalid_json_after_retry_as_failed(tmp_path, monkeypatch):
    monkeypatch.setattr(ollama_client.SESSION, "post", fake_post_returning("{not json", "{still not"))
    case_dir = write_case(tmp_path / "sync", MEETING_EXPECTED)

    result = run.run_case(case_dir, "test-model", private=False)

    assert result.failed is True
    assert result.scores["action_items"] == FieldScore(matched=0, expected=1, extracted=0)


def test_run_case_raises_when_ollama_is_unreachable(tmp_path, monkeypatch):
    def fake_post(url, json, timeout):
        raise requests.RequestException("connection refused")

    monkeypatch.setattr(ollama_client.SESSION, "post", fake_post)
    case_dir = write_case(tmp_path / "sync", MEETING_EXPECTED)

    with pytest.raises(RuntimeError, match="Ollama request failed"):
        run.run_case(case_dir, "test-model", private=False)


def test_results_rows_name_public_cases_but_never_private_ones():
    scores = {"action_items": FieldScore(1, 1, 1), "decisions": FieldScore(0, 0, 0)}
    public = [CaseResult("meeting-sync", False, scores, retried=True, failed=False)]
    private = [CaseResult("acme-real-call", True, scores, retried=False, failed=False)]

    public_row = run.results_row("public", public, "qwen2.5:7b", "abc1234", "baseline", date(2026, 9, 28))
    private_row = run.results_row("private", private, "qwen2.5:7b", "abc1234", "baseline", date(2026, 9, 28))

    assert public_row.startswith("| 2026-09-28 | abc1234 | qwen2.5:7b | baseline | public (1) |")
    assert "meeting-sync 1.00 / 1.00" in public_row
    assert "1/1" in public_row
    assert "private (1)" in private_row
    assert "acme-real-call" not in private_row
