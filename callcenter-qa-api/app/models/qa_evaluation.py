import uuid

from sqlalchemy import Boolean, ForeignKey, Numeric, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import IdMixin, TimestampMixin

STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"

SOURCE_RULE = "rule"
SOURCE_LOCAL_LLM = "local_llm"


class QAEvaluation(Base, IdMixin, TimestampMixin):
    __tablename__ = "qa_evaluations"

    call_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("calls.id"), index=True
    )
    rubric_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rubric_versions.id")
    )
    # Computed programmatically from weighted per-criterion scores - never
    # trusted directly from the LLM's self-reported number. See
    # app/qa_evaluation/scoring.py:compute_weighted_overall.
    overall_score: Mapped[float | None] = mapped_column(Numeric(5, 2), default=None)
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    flags: Mapped[list | None] = mapped_column(JSONB, default=None)
    raw_llm_response: Mapped[dict | None] = mapped_column(JSONB, default=None)
    # Exact rendered system prompt used for this evaluation, so results stay
    # reproducible/auditable even if the rubric or prompt template changes later.
    system_prompt_snapshot: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[str] = mapped_column(default=STATUS_COMPLETED)
    error_message: Mapped[str | None] = mapped_column(Text, default=None)

    call: Mapped["Call"] = relationship(back_populates="qa_evaluations")  # noqa: F821
    rubric_version: Mapped["RubricVersion"] = relationship()  # noqa: F821
    scores: Mapped[list["QAEvaluationScore"]] = relationship(
        back_populates="qa_evaluation", cascade="all, delete-orphan"
    )


class QAEvaluationScore(Base, IdMixin):
    __tablename__ = "qa_evaluation_scores"
    __table_args__ = (UniqueConstraint("qa_evaluation_id", "rubric_criterion_id"),)

    qa_evaluation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("qa_evaluations.id"), index=True
    )
    rubric_criterion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rubric_criteria.id")
    )
    score: Mapped[float] = mapped_column(Numeric(5, 2))
    rationale: Mapped[str | None] = mapped_column(Text, default=None)
    source: Mapped[str] = mapped_column(default=SOURCE_LOCAL_LLM)

    # Evidence: a verbatim excerpt the score is grounded in. quote_verified is
    # only True once app/qa_evaluation/evidence.py has confirmed the quote
    # actually occurs in the transcript - an unverified LLM quote is never
    # trusted and is surfaced as such rather than silently kept.
    quote: Mapped[str | None] = mapped_column(Text, default=None)
    quote_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    evidence_start: Mapped[float | None] = mapped_column(Numeric(10, 2), default=None)
    evidence_end: Mapped[float | None] = mapped_column(Numeric(10, 2), default=None)
    evidence_speaker: Mapped[str | None] = mapped_column(default=None)

    qa_evaluation: Mapped["QAEvaluation"] = relationship(back_populates="scores")
    rubric_criterion: Mapped["RubricCriterion"] = relationship()  # noqa: F821
