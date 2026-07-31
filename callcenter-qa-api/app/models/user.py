import uuid
from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import IdMixin, TimestampMixin

ROLE_SUPER_ADMIN = "super_admin"
ROLE_ADMIN = "admin"
ROLE_QA_MANAGER = "qa_manager"
ROLE_TEAM_LEAD = "team_lead"
ROLE_REVIEWER = "reviewer"
ROLE_AGENT = "agent"
ROLE_VIEWER = "viewer"

ALL_ROLES = (
    ROLE_SUPER_ADMIN,
    ROLE_ADMIN,
    ROLE_QA_MANAGER,
    ROLE_TEAM_LEAD,
    ROLE_REVIEWER,
    ROLE_AGENT,
    ROLE_VIEWER,
)


class User(Base, IdMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(unique=True, index=True)
    password_hash: Mapped[str]
    role: Mapped[str] = mapped_column(default=ROLE_VIEWER)
    is_active: Mapped[bool] = mapped_column(default=True)
    failed_login_count: Mapped[int] = mapped_column(default=0)
    locked_until: Mapped[datetime | None] = mapped_column(default=None)

    # team_id scopes team_lead/reviewer visibility; agent_id links an
    # `agent`-role login to the specific Agent row they may see calls for.
    team_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id"), default=None
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), default=None
    )

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class RefreshToken(Base, IdMixin, TimestampMixin):
    """Refresh tokens are opaque random strings; only a SHA-256 hash is
    stored, so a stolen DB backup can't be replayed as a live token. Revoking
    (revoked_at set) is how logout / logout-all-devices actually works -
    unlike the access token, this cannot be undone by re-verifying a JWT
    signature."""

    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )
    token_hash: Mapped[str] = mapped_column(unique=True, index=True)
    expires_at: Mapped[datetime]
    revoked_at: Mapped[datetime | None] = mapped_column(default=None)

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")


class LoginAttempt(Base, IdMixin, TimestampMixin):
    """Append-only login journal - every attempt, success or failure."""

    __tablename__ = "login_attempts"

    email: Mapped[str] = mapped_column(index=True)
    success: Mapped[bool]
    ip_address: Mapped[str | None] = mapped_column(default=None)
