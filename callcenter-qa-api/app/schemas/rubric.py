import uuid

from pydantic import BaseModel, ConfigDict


class RubricCriterionCreate(BaseModel):
    key: str
    label: str
    description: str
    category: str | None = None
    weight: float = 1.0
    max_score: int = 5
    is_required: bool = False
    is_critical: bool = False
    applies_to: str = "call"
    display_order: int = 0
    examples_positive: list[str] | None = None
    examples_negative: list[str] | None = None
    required_phrases: list[str] | None = None
    forbidden_phrases: list[str] | None = None


class RubricCriterionUpdate(BaseModel):
    label: str | None = None
    description: str | None = None
    category: str | None = None
    weight: float | None = None
    max_score: int | None = None
    is_required: bool | None = None
    is_critical: bool | None = None
    applies_to: str | None = None
    display_order: int | None = None
    is_active: bool | None = None
    examples_positive: list[str] | None = None
    examples_negative: list[str] | None = None
    required_phrases: list[str] | None = None
    forbidden_phrases: list[str] | None = None


class RubricCriterionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    key: str
    label: str
    description: str
    category: str | None
    weight: float
    max_score: int
    is_required: bool
    is_critical: bool
    applies_to: str
    display_order: int
    is_active: bool
    examples_positive: list[str] | None
    examples_negative: list[str] | None
    required_phrases: list[str] | None
    forbidden_phrases: list[str] | None


class RubricVersionCriterionInput(BaseModel):
    rubric_criterion_id: uuid.UUID
    weight: float = 1.0


class RubricVersionCreate(BaseModel):
    name: str
    llm_model_id: str
    criteria: list[RubricVersionCriterionInput]


class RubricVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version_number: int
    name: str
    llm_model_id: str
    is_active: bool
