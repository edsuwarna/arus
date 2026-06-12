"""009_add_transform_tables

Add transform_config column to pipeline_tables and create transform_scripts table.
"""
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade():
    # Add transform_config JSON column to pipeline_tables
    op.add_column(
        "pipeline_tables",
        sa.Column("transform_config", sa.JSON, nullable=True),
        schema="arus_config",
    )

    # Create transform_scripts table
    op.create_table(
        "transform_scripts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("pipeline_id", UUID, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema="arus_config",
    )

    op.create_unique_constraint(
        "uq_transform_scripts_pipeline_name",
        "transform_scripts",
        ["pipeline_id", "name"],
        schema="arus_config",
    )

    op.create_foreign_key(
        "fk_ts_pipeline",
        "transform_scripts", "pipelines",
        ["pipeline_id"], ["id"],
        source_schema="arus_config", referent_schema="arus_config",
        ondelete="CASCADE",
    )


def downgrade():
    op.drop_constraint(
        "fk_ts_pipeline",
        "transform_scripts",
        schema="arus_config",
    )
    op.drop_table("transform_scripts", schema="arus_config")
    op.drop_column("pipeline_tables", "transform_config", schema="arus_config")
