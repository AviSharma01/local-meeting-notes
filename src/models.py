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
    decisions: list[Decision]
    action_items: list[ActionItem]
    follow_ups: list[str]
    risks: list[str]
    open_questions: list[str]
    needs_review: list[str]
