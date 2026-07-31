"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-07-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=False),
        sa.Column("external_agent_id", sa.String(), nullable=True),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("team", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.create_index("ix_agents_organization_id", "agents", ["organization_id"])

    op.create_table(
        "calls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=False),
        sa.Column(
            "agent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agents.id"),
            nullable=False,
        ),
        sa.Column("call_date", sa.TIMESTAMP(), nullable=False),
        sa.Column("direction", sa.String(), nullable=True),
        sa.Column("queue", sa.String(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("audio_storage_key", sa.String(), nullable=False),
        sa.Column("original_filename", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="uploaded"),
        sa.Column("updated_at", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_calls_organization_id", "calls", ["organization_id"])
    op.create_index("ix_calls_agent_id", "calls", ["agent_id"])
    op.create_index("ix_calls_status", "calls", ["status"])

    op.create_table(
        "transcripts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=False),
        sa.Column(
            "call_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("calls.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("full_text", sa.Text(), nullable=False),
        sa.Column("segments", postgresql.JSONB(), nullable=False),
        sa.Column("engine", sa.String(), nullable=False),
        sa.Column("engine_model", sa.String(), nullable=False),
        sa.Column("language", sa.String(), nullable=True),
    )
    op.create_index("ix_transcripts_call_id", "transcripts", ["call_id"])

    op.create_table(
        "rubric_criteria",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=False),
        sa.Column("key", sa.String(), nullable=False, unique=True),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("weight", sa.Numeric(4, 2), nullable=False, server_default="1.0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )

    op.create_table(
        "rubric_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("llm_model_id", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    op.create_table(
        "rubric_version_criteria",
        sa.Column(
            "rubric_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("rubric_versions.id"),
            primary_key=True,
        ),
        sa.Column(
            "rubric_criterion_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("rubric_criteria.id"),
            primary_key=True,
        ),
        sa.Column("weight", sa.Numeric(4, 2), nullable=False, server_default="1.0"),
    )

    op.create_table(
        "qa_evaluations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=False),
        sa.Column(
            "call_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("calls.id"), nullable=False
        ),
        sa.Column(
            "rubric_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("rubric_versions.id"),
            nullable=False,
        ),
        sa.Column("overall_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("flags", postgresql.JSONB(), nullable=True),
        sa.Column("raw_llm_response", postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="completed"),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_index("ix_qa_evaluations_call_id", "qa_evaluations", ["call_id"])

    op.create_table(
        "qa_evaluation_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "qa_evaluation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("qa_evaluations.id"),
            nullable=False,
        ),
        sa.Column(
            "rubric_criterion_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("rubric_criteria.id"),
            nullable=False,
        ),
        sa.Column("score", sa.Numeric(5, 2), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.UniqueConstraint("qa_evaluation_id", "rubric_criterion_id"),
    )
    op.create_index("ix_qa_evaluation_scores_qa_evaluation_id", "qa_evaluation_scores", ["qa_evaluation_id"])


def downgrade() -> None:
    op.drop_table("qa_evaluation_scores")
    op.drop_table("qa_evaluations")
    op.drop_table("rubric_version_criteria")
    op.drop_table("rubric_versions")
    op.drop_table("rubric_criteria")
    op.drop_table("transcripts")
    op.drop_table("calls")
    op.drop_table("agents")
