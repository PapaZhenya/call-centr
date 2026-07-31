import uuid

from sqlalchemy import ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import IdMixin, TimestampMixin

APPLIES_TO_AGENT = "agent"
APPLIES_TO_CLIENT = "client"
APPLIES_TO_CALL = "call"


class RubricCriterion(Base, IdMixin, TimestampMixin):
    __tablename__ = "rubric_criteria"

    key: Mapped[str] = mapped_column(unique=True)  # stable machine key, e.g. 'script_adherence'
    label: Mapped[str]  # human-readable, e.g. 'Script Adherence'
    description: Mapped[str] = mapped_column(Text)  # instructions shown to the LLM
    category: Mapped[str | None] = mapped_column(default=None)
    weight: Mapped[float] = mapped_column(Numeric(4, 2), default=1.0)
    max_score: Mapped[int] = mapped_column(default=5)
    is_required: Mapped[bool] = mapped_column(default=False)
    is_critical: Mapped[bool] = mapped_column(default=False)  # a low score here forces a critical flag
    applies_to: Mapped[str] = mapped_column(default=APPLIES_TO_CALL)
    display_order: Mapped[int] = mapped_column(default=0)
    is_active: Mapped[bool] = mapped_column(default=True)

    examples_positive: Mapped[list | None] = mapped_column(JSONB, default=None)
    examples_negative: Mapped[list | None] = mapped_column(JSONB, default=None)

    # If either list is non-empty, this criterion is scored deterministically
    # by app/qa_evaluation/rules.py (source="rule") and excluded from the LLM
    # schema entirely - see app/qa_evaluation/rubric_schema.py.
    required_phrases: Mapped[list | None] = mapped_column(JSONB, default=None)
    forbidden_phrases: Mapped[list | None] = mapped_column(JSONB, default=None)

    @property
    def is_rule_based(self) -> bool:
        return bool(self.required_phrases) or bool(self.forbidden_phrases)


class RubricVersion(Base, IdMixin, TimestampMixin):
    __tablename__ = "rubric_versions"

    version_number: Mapped[int]
    name: Mapped[str]
    # Informational: the local model configured (LOCAL_LLM_MODEL) when this
    # version was created. Evaluations always use the currently configured
    # local model - see app/llm/factory.py - this field is provenance, not
    # a per-version override.
    llm_model_id: Mapped[str]
    is_active: Mapped[bool] = mapped_column(default=False)  # only one active version at a time

    criteria_links: Mapped[list["RubricVersionCriterion"]] = relationship(
        back_populates="rubric_version"
    )


class RubricVersionCriterion(Base):
    __tablename__ = "rubric_version_criteria"

    rubric_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rubric_versions.id"), primary_key=True
    )
    rubric_criterion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rubric_criteria.id"), primary_key=True
    )
    weight: Mapped[float] = mapped_column(Numeric(4, 2), default=1.0)

    rubric_version: Mapped["RubricVersion"] = relationship(back_populates="criteria_links")
    rubric_criterion: Mapped["RubricCriterion"] = relationship()
