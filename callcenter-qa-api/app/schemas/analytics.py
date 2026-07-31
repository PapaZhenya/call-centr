import uuid
from datetime import datetime

from pydantic import BaseModel


class AgentSummary(BaseModel):
    agent_id: uuid.UUID
    call_count: int
    average_score: float | None


class ScoreByCriterion(BaseModel):
    rubric_criterion_id: uuid.UUID
    key: str
    label: str
    average_score: float | None
    count: int


class TrendPoint(BaseModel):
    period: datetime
    average_score: float | None
    call_count: int


class CriterionAverage(BaseModel):
    key: str
    label: str
    average_score: float | None


class OrgOverview(BaseModel):
    total_calls: int
    average_score: float | None
    worst_criterion: CriterionAverage | None
    best_criterion: CriterionAverage | None
    criteria: list[CriterionAverage]
