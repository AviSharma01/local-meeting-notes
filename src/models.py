from typing import Annotated

from pydantic import BaseModel, BeforeValidator


NULL_STRINGS = {"null", "none", ""}


def _none_if_null(value):
    """Treat "null", "none", and blank strings from the model as a missing value."""
    if isinstance(value, str) and value.strip().lower() in NULL_STRINGS:
        return None
    return value


OptionalText = Annotated[str | None, BeforeValidator(_none_if_null)]


class Decision(BaseModel):
    text: str
    evidence: OptionalText = None


class ActionItem(BaseModel):
    task: str
    owner: OptionalText = None
    due: OptionalText = None
    evidence: OptionalText = None


class MeetingExtraction(BaseModel):
    summary: str
    decisions: list[Decision] = []
    action_items: list[ActionItem] = []
    follow_ups: list[str] = []
    risks: list[str] = []
    open_questions: list[str] = []
    needs_review: list[str] = []


class Person(BaseModel):
    name: str
    role: OptionalText = None


class DebriefExtraction(BaseModel):
    summary: str
    questions_asked: list[str] = []
    weak_spots: list[str] = []
    people_mentioned: list[Person] = []
    commitments: list[ActionItem] = []
    open_questions: list[str] = []
