"""teams table, agent/user team scoping, full RBAC roles

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "teams",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
    )
    op.create_index("ix_teams_organization_id", "teams", ["organization_id"])

    # agents: replace free-text `team` column with a real FK
    op.add_column(
        "agents",
        sa.Column("team_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("teams.id"), nullable=True),
    )
    op.create_index("ix_agents_team_id", "agents", ["team_id"])
    op.drop_column("agents", "team")

    # users: RBAC scoping columns
    op.add_column(
        "users",
        sa.Column("team_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("teams.id"), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "agent_id")
    op.drop_column("users", "team_id")

    op.add_column("agents", sa.Column("team", sa.String(), nullable=True))
    op.drop_index("ix_agents_team_id", table_name="agents")
    op.drop_column("agents", "team_id")

    op.drop_index("ix_teams_organization_id", table_name="teams")
    op.drop_table("teams")
