from pydantic import BaseModel


class TaskModerationInput(BaseModel):
    title: str
    description: str
    category: str
    evidence_requirements: list[dict] = []
    country: str | None = None
    city: str | None = None
    location_mode: str = "remote"


class ModerationResult(BaseModel):
    decision: str  # allow, manual_review, reject
    risk_level: str  # low, medium, high
    matched_rules: list[str]
    explanation: str
