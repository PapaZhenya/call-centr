import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import IdMixin, OrganizationMixin, TimestampMixin


class Agent(Base, IdMixin, OrganizationMixin, TimestampMixin):
    __tablename__ = "agents"

    external_agent_id: Mapped[str | None] = mapped_column(default=None)
    display_name: Mapped[str]
    team_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id"), default=None, index=True
    )
    is_active: Mapped[bool] = mapped_column(default=True)

    team: Mapped["Team | None"] = relationship(back_populates="agents")  # noqa: F821
    calls: Mapped[list["Call"]] = relationship(back_populates="agent")  # noqa: F821
