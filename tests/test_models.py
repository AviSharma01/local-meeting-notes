import pytest
from pydantic import ValidationError

from src.models import ActionItem, DebriefExtraction, MeetingExtraction, Person


def test_meeting_extraction_validates_complete_payload():
    extraction = MeetingExtraction.model_validate(
        {
            "summary": "Launch planning.",
            "decisions": [{"text": "Keep the launch date", "evidence": "[00:50]"}],
            "action_items": [
                {"task": "QA pass", "owner": "Sam", "due": "Friday", "evidence": "[00:35]"}
            ],
            "follow_ups": ["Check docs"],
            "risks": [],
            "open_questions": [],
            "needs_review": [],
        }
    )

    assert extraction.decisions[0].text == "Keep the launch date"
    assert extraction.action_items[0].owner == "Sam"


def test_action_item_optional_fields_default_to_none():
    item = ActionItem(task="Send notes")

    assert item.owner is None
    assert item.due is None
    assert item.evidence is None


def test_meeting_extraction_rejects_missing_summary():
    with pytest.raises(ValidationError):
        MeetingExtraction.model_validate({"decisions": []})


def test_meeting_extraction_defaults_missing_lists_to_empty():
    extraction = MeetingExtraction.model_validate(
        {"summary": "Launch planning.", "open_questions": []}
    )

    assert extraction.decisions == []
    assert extraction.action_items == []
    assert extraction.follow_ups == []
    assert extraction.risks == []
    assert extraction.needs_review == []


def test_meeting_extraction_rejects_wrong_types():
    with pytest.raises(ValidationError):
        MeetingExtraction.model_validate(
            {
                "summary": "Launch planning.",
                "decisions": "none",
                "action_items": [],
                "follow_ups": [],
                "risks": [],
                "open_questions": [],
                "needs_review": [],
            }
        )


def test_debrief_extraction_validates_complete_payload():
    extraction = DebriefExtraction.model_validate(
        {
            "summary": "First technical round.",
            "questions_asked": ["Write a 7-day retention query"],
            "weak_spots": ["Window functions"],
            "people_mentioned": [
                {"name": "Priya Raman", "role": "Analytics manager"},
                {"name": "Tong", "role": None},
            ],
            "commitments": [
                {"task": "Send portfolio link", "owner": "Me", "due": "Friday, October 3rd"}
            ],
            "open_questions": ["Salary range"],
        }
    )

    assert extraction.people_mentioned[0] == Person(name="Priya Raman", role="Analytics manager")
    assert extraction.people_mentioned[1].role is None
    assert extraction.commitments[0].owner == "Me"


def test_person_role_defaults_to_none():
    assert Person(name="Tong").role is None


def test_debrief_extraction_defaults_missing_lists_to_empty():
    extraction = DebriefExtraction.model_validate({"summary": "Short call."})

    assert extraction.questions_asked == []
    assert extraction.weak_spots == []
    assert extraction.people_mentioned == []
    assert extraction.commitments == []
    assert extraction.open_questions == []


def test_debrief_extraction_rejects_missing_summary():
    with pytest.raises(ValidationError):
        DebriefExtraction.model_validate({"weak_spots": []})


def test_debrief_extraction_rejects_wrong_types():
    with pytest.raises(ValidationError):
        DebriefExtraction.model_validate({"summary": "Call.", "people_mentioned": ["Priya"]})
