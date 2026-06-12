"""008_add_notification_tables

Add notification_targets and pipeline_notifications tables.
"""
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ARRAY

revision = "008"
down_revision = "007_add_pipeline_load_mode"
branch_labels = None
depends_on = None


def upgrade():
    # notification_targets
    op.create_table(
        "notification_targets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("config", sa.Text, nullable=False),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema="arus_config",
    )

    # pipeline_notifications
    op.create_table(
        "pipeline_notifications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("pipeline_id", UUID, nullable=False),
        sa.Column("target_id", UUID, nullable=False),
        sa.Column("event_types", ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema="arus_config",
    )

    op.create_foreign_key(
        "fk_pn_pipeline",
        "pipeline_notifications", "pipelines",
        ["pipeline_id"], ["id"],
        source_schema="arus_config", referent_schema="arus_config",
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_pn_target",
        "pipeline_notifications", "notification_targets",
        ["target_id"], ["id"],
        source_schema="arus_config", referent_schema="arus_config",
        ondelete="CASCADE",
    )


def downgrade():
    op.drop_table("pipeline_notifications", schema="arus_config")
    op.drop_table("notification_targets", schema="arus_config")
