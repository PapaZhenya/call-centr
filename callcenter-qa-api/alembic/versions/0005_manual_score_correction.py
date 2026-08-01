"""manual score correction fields on qa_evaluation_scores

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("qa_evaluation_scores", sa.Column("manual_score", sa.Numeric(5, 2), nullable=True))
    op.add_column("qa_evaluation_scores", sa.Column("manual_comment", sa.Text(), nullable=True))
    op.add_column(
        "qa_evaluation_scores",
        sa.Column(
            "corrected_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
    )
    op.add_column(
        "qa_evaluation_scores",
        sa.Column("corrected_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("qa_evaluation_scores", "corrected_at")
    op.drop_column("qa_evaluation_scores", "corrected_by_user_id")
    op.drop_column("qa_evaluation_scores", "manual_comment")
    op.drop_column("qa_evaluation_scores", "manual_score")
