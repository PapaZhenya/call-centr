import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import IdMixin, OrganizationMixin, TimestampMixin

# Call.status state machine:
# uploaded -> transcribing -> transcribed -> evaluating -> completed
#                  \-> transcription_failed        \-> evaluation_failed
STATUS_UPLOADED = "uploaded"
STATUS_TRANSCRIBING = "transcribing"
STATUS_TRANSCRIBED = "transcribed"
STATUS_TRANSCRIPTION_FAILED = "transcription_failed"
STATUS_EVALUATING = "evaluating"
STATUS_COMPLETED = "completed"
STATUS_EVALUATION_FAILED = "evaluation_failed"


class Call(Base, IdMixin, OrganizationMixin, TimestampMixin):
    __tablename__ = "calls"

    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), index=True
    )
    call_date: Mapped[datetime]
    direction: Mapped[str | None] = mapped_column(default=None)
    queue: Mapped[str | None] = mapped_column(default=None)
    duration_seconds: Mapped[int | None] = mapped_column(default=None)
    audio_storage_key: Mapped[str]
    original_filename: Mapped[str]
    status: Mapped[str] = mapped_column(default=STATUS_UPLOADED, index=True)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    agent: Mapped["Agent"] = relationship(back_populates="calls")  # noqa: F821
    transcript: Mapped["Transcript | None"] = relationship(  # noqa: F821
        back_populates="call", uselist=False
    )
    qa_evaluations: Mapped[list["QAEvaluation"]] = relationship(back_populates="call")  # noqa: F821
