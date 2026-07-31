import uuid

from pydantic import BaseModel, ConfigDict


class RubricCriterionSummary(BaseModel):
    """Minimal criterion info embedded in a score, so the frontend can render
    a score without a second round-trip to /rubric/criteria."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    key: str
    label: str
    category: str | None


class QAEvaluationScoreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rubric_criterion_id: uuid.UUID
    rubric_criterion: RubricCriterionSummary
    score: float
    rationale: str | None
    source: str
    quote: str | None
    quote_verified: bool
    evidence_start: float | None
    evidence_end: float | None
    evidence_speaker: str | None


class QAEvaluationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    call_id: uuid.UUID
    rubric_version_id: uuid.UUID
    overall_score: float | None
    notes: str | None
    flags: list | None
    status: str
    error_message: str | None
    scores: list[QAEvaluationScoreRead]
