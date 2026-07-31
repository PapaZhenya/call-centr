import uuid
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

# Single-tenant MVP: every table carries a nullable organization_id so
# multi-tenancy can be turned on later (scoped queries + a resolved org_id)
# without an expensive backfill migration.
DEFAULT_ORGANIZATION_ID: uuid.UUID = uuid.UUID("00000000-0000-0000-0000-000000000001")


class IdMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class OrganizationMixin:
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, default=DEFAULT_ORGANIZATION_ID, index=True
    )
