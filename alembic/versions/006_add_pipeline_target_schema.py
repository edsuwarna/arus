"""Add target_schema to pipelines, deprecate destination target_schema

Now schema is determined at pipeline level:
  per-table override → pipeline.target_schema → "public"

Revision ID: 006_add_pipeline_target_schema
Revises: 005_add_schema_target
Create Date: 2026-06-12
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "006_add_pipeline_target_schema"
down_revision = "005_add_schema_target"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add target_schema to pipelines table (pipeline-level default)
    op.execute(
        "ALTER TABLE arus_config.pipelines ADD COLUMN IF NOT EXISTS target_schema VARCHAR(255) DEFAULT 'public'"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE arus_config.pipelines DROP COLUMN IF EXISTS target_schema"
    )
