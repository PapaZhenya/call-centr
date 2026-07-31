"""local LLM rubric fields, evidence/source on scores, auth tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- rubric_criteria: new fields for a real checklist editor -----------
    op.add_column("rubric_criteria", sa.Column("category", sa.String(), nullable=True))
    op.add_column(
        "rubric_criteria",
        sa.Column("max_score", sa.Integer(), nullable=False, server_default="5"),
    )
    op.add_column(
        "rubric_criteria",
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "rubric_criteria",
        sa.Column("is_critical", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "rubric_criteria",
        sa.Column("applies_to", sa.String(), nullable=False, server_default="call"),
    )
    op.add_column(
        "rubric_criteria",
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "rubric_criteria", sa.Column("examples_positive", postgresql.JSONB(), nullable=True)
    )
    op.add_column(
        "rubric_criteria", sa.Column("examples_negative", postgresql.JSONB(), nullable=True)
    )
    op.add_column(
        "rubric_criteria", sa.Column("required_phrases", postgresql.JSONB(), nullable=True)
    )
    op.add_column(
        "rubric_criteria", sa.Column("forbidden_phrases", postgresql.JSONB(), nullable=True)
    )

    # --- qa_evaluations: reproducibility snapshot ---------------------------
    op.add_column(
        "qa_evaluations", sa.Column("system_prompt_snapshot", sa.Text(), nullable=True)
    )

    # --- qa_evaluation_scores: evidence + scoring source --------------------
    op.add_column(
        "qa_evaluation_scores",
        sa.Column("source", sa.String(), nullable=False, server_default="local_llm"),
    )
    op.add_column("qa_evaluation_scores", sa.Column("quote", sa.Text(), nullable=True))
    op.add_column(
        "qa_evaluation_scores",
        sa.Column("quote_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "qa_evaluation_scores", sa.Column("evidence_start", sa.Numeric(10, 2), nullable=True)
    )
    op.add_column(
        "qa_evaluation_scores", sa.Column("evidence_end", sa.Numeric(10, 2), nullable=True)
    )
    op.add_column(
        "qa_evaluation_scores", sa.Column("evidence_speaker", sa.String(), nullable=True)
    )

    # --- auth: users / refresh_tokens / login_attempts ----------------------
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=False),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False, server_default="viewer"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("failed_login_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_until", sa.TIMESTAMP(), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=False),
        sa.Column(
            "user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("token_hash", sa.String(), nullable=False, unique=True),
        sa.Column("expires_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("revoked_at", sa.TIMESTAMP(), nullable=True),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"])

    op.create_table(
        "login_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("ip_address", sa.String(), nullable=True),
    )
    op.create_index("ix_login_attempts_email", "login_attempts", ["email"])


def downgrade() -> None:
    op.drop_table("login_attempts")
    op.drop_table("refresh_tokens")
    op.drop_table("users")

    op.drop_column("qa_evaluation_scores", "evidence_speaker")
    op.drop_column("qa_evaluation_scores", "evidence_end")
    op.drop_column("qa_evaluation_scores", "evidence_start")
    op.drop_column("qa_evaluation_scores", "quote_verified")
    op.drop_column("qa_evaluation_scores", "quote")
    op.drop_column("qa_evaluation_scores", "source")

    op.drop_column("qa_evaluations", "system_prompt_snapshot")

    op.drop_column("rubric_criteria", "forbidden_phrases")
    op.drop_column("rubric_criteria", "required_phrases")
    op.drop_column("rubric_criteria", "examples_negative")
    op.drop_column("rubric_criteria", "examples_positive")
    op.drop_column("rubric_criteria", "display_order")
    op.drop_column("rubric_criteria", "applies_to")
    op.drop_column("rubric_criteria", "is_critical")
    op.drop_column("rubric_criteria", "is_required")
    op.drop_column("rubric_criteria", "max_score")
    op.drop_column("rubric_criteria", "category")
