from sqlalchemy.orm import Mapped, relationship

from app.database import Base
from app.models.base import IdMixin, OrganizationMixin, TimestampMixin


class Team(Base, IdMixin, OrganizationMixin, TimestampMixin):
    __tablename__ = "teams"

    name: Mapped[str]

    agents: Mapped[list["Agent"]] = relationship(back_populates="team")  # noqa: F821
