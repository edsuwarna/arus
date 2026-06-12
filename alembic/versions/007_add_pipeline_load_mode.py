"""Add load_mode to pipelines table (pipeline-level default)

Revision ID: 007_add_pipeline_load_mode
Revises: 006_add_pipeline_target_schema
Create Date: 2026-06-12
"""
from alembic import op

# revision identifiers
revision = "007_add_pipeline_load_mode"
down_revision = "006_add_pipeline_target_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE arus_config.pipelines ADD COLUMN IF NOT EXISTS load_mode VARCHAR(20) DEFAULT 'direct'"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE arus_config.pipelines DROP COLUMN IF EXISTS load_mode"
    )
