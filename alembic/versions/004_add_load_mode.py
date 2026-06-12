"""Add load_mode column to pipeline_tables

Revision ID: 004_add_load_mode
Revises: 003_rename_analytics_to_target
Create Date: 2026-06-12
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '004_add_load_mode'
down_revision = '003_rename_analytics_to_target'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE arus_config.pipeline_tables ADD COLUMN IF NOT EXISTS load_mode VARCHAR(20) DEFAULT 'direct'"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE arus_config.pipeline_tables DROP COLUMN IF EXISTS load_mode"
    )
