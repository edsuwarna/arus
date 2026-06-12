"""rename analytics_schema to target_schema (already applied)

Revision ID: 003_rename_analytics_to_target
Revises: 002_add_mongo_source_fields
Create Date: 2025-06-12
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '003_rename_analytics_to_target'
down_revision: Union[str, None] = '002_add_mongo_source_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename analytics_schema → target_schema, safe to re-run
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'arus_config' AND table_name = 'destinations'
                AND column_name = 'analytics_schema'
            ) THEN
                ALTER TABLE arus_config.destinations RENAME COLUMN analytics_schema TO target_schema;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'arus_config' AND table_name = 'destinations'
                AND column_name = 'target_schema'
            ) THEN
                ALTER TABLE arus_config.destinations RENAME COLUMN target_schema TO analytics_schema;
            END IF;
        END $$;
    """)
