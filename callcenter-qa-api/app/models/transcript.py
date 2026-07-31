import uuid

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import IdMixin, TimestampMixin


class Transcript(Base, IdMixin, TimestampMixin):
    __tablename__ = "transcripts"

    call_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("calls.id"), unique=True, index=True
    )
    full_text: Mapped[str] = mapped_column(Text)
    segments: Mapped[list] = mapped_column(JSONB)  # [{speaker, start, end, text}, ...]
    engine: Mapped[str]  # provenance, e.g. 'faster_whisper' - future ASR swap seam
    engine_model: Mapped[str]  # e.g. 'small'
    language: Mapped[str | None] = mapped_column(default=None)

    call: Mapped["Call"] = relationship(back_populates="transcript")  # noqa: F821
