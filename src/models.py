from pydantic import BaseModel


class Decision(BaseModel):
    text: str
    evidence: str | None = None


class ActionItem(BaseModel):
    task: str
    owner: str | None = None
    due: str | None = None
    evidence: str | None = None


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
    role: str | None = None


class DebriefExtraction(BaseModel):
    summary: str
    questions_asked: list[str] = []
    weak_spots: list[str] = []
    people_mentioned: list[Person] = []
    commitments: list[ActionItem] = []
    open_questions: list[str] = []
