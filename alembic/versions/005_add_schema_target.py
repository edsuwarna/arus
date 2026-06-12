"""Add schema_include to sources, target_schema to pipeline_tables

Revision ID: 005_add_schema_target
Revises: 004_add_load_mode
Create Date: 2026-06-12
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY

# revision identifiers
revision = "005_add_schema_target"
down_revision = "004_add_load_mode"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE arus_config.sources ADD COLUMN IF NOT EXISTS schema_include VARCHAR[] DEFAULT '{}'"
    )
    op.execute(
        "ALTER TABLE arus_config.pipeline_tables ADD COLUMN IF NOT EXISTS target_schema VARCHAR(255)"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE arus_config.sources DROP COLUMN IF EXISTS schema_include"
    )
    op.execute(
        "ALTER TABLE arus_config.pipeline_tables DROP COLUMN IF EXISTS target_schema"
    )
