"""convert all naive TIMESTAMP columns to timestamptz

The app writes aware-UTC datetimes (datetime.now(timezone.utc)) everywhere;
asyncpg rejects aware values for TIMESTAMP WITHOUT TIME ZONE columns. All
values stored so far came from Postgres now() in a UTC-timezone container,
so reinterpreting them as UTC is lossless.

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-31

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        DECLARE r record;
        BEGIN
            FOR r IN
                SELECT table_name, column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND data_type = 'timestamp without time zone'
                  AND table_name <> 'alembic_version'
            LOOP
                EXECUTE format(
                    'ALTER TABLE %I ALTER COLUMN %I TYPE timestamptz USING %I AT TIME ZONE ''UTC''',
                    r.table_name, r.column_name, r.column_name
                );
            END LOOP;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        DECLARE r record;
        BEGIN
            FOR r IN
                SELECT table_name, column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND data_type = 'timestamp with time zone'
                  AND table_name <> 'alembic_version'
            LOOP
                EXECUTE format(
                    'ALTER TABLE %I ALTER COLUMN %I TYPE timestamp USING %I AT TIME ZONE ''UTC''',
                    r.table_name, r.column_name, r.column_name
                );
            END LOOP;
        END $$;
        """
    )
