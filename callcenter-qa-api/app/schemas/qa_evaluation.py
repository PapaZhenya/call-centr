import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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
    manual_score: float | None
    manual_comment: str | None
    corrected_at: datetime | None


class ScoreCorrectionInput(BaseModel):
    # None clears the correction and reverts to the model's score.
    manual_score: float | None = Field(default=None, ge=0, le=10)
    comment: str | None = None


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
