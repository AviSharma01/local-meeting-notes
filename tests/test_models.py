import pytest
from pydantic import ValidationError

from src.models import ActionItem, MeetingExtraction


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


def test_meeting_extraction_rejects_missing_fields():
    with pytest.raises(ValidationError):
        MeetingExtraction.model_validate({"summary": "Only a summary."})


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
