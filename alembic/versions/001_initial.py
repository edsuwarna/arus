"""Initial migration: create all schemas and tables.

Revision ID: 001_initial
Revises:
Create Date: 2025-06-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ============ SCHEMAS ============
    for schema in ["arus_config", "arus_state", "staging", "analytics", "arus_run_logs"]:
        op.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")

    # ============ arus_config.users ============
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="viewer"),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema="arus_config",
    )

    # ============ arus_config.sources ============
    op.create_table(
        "sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("host", sa.String(255), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column("database", sa.String(255), nullable=False),
        sa.Column("username", sa.String(255), nullable=False),
        sa.Column("password_enc", sa.Text(), nullable=False),
        sa.Column("ssl", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("sync_method", sa.String(20), server_default="auto"),
        sa.Column("table_include", postgresql.ARRAY(sa.String()), server_default="{}"),
        sa.Column("table_exclude", postgresql.ARRAY(sa.String()), server_default="{}"),
        sa.Column("status", sa.String(20), server_default="registered"),
        sa.Column("last_tested", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema="arus_config",
    )

    # ============ arus_config.destinations ============
    op.create_table(
        "destinations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("host", sa.String(255), nullable=True),
        sa.Column("port", sa.Integer(), nullable=True),
        sa.Column("database", sa.String(255), nullable=True),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("password_enc", sa.Text(), nullable=True),
        sa.Column("ssl", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("raw_schema", sa.String(255), server_default="staging"),
        sa.Column("analytics_schema", sa.String(255), server_default="analytics"),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("status", sa.String(20), server_default="registered"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema="arus_config",
    )

    # ============ arus_config.pipelines ============
    op.create_table(
        "pipelines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("source_id", postgresql.UUID(),
                  sa.ForeignKey("arus_config.sources.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("destination_id", postgresql.UUID(),
                  sa.ForeignKey("arus_config.destinations.id", ondelete="RESTRICT"),
                  nullable=False),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("schedule", sa.String(100), nullable=True),
        sa.Column("max_retries", sa.Integer(), server_default=sa.text("3")),
        sa.Column("timeout_seconds", sa.Integer(), server_default=sa.text("300")),
        sa.Column("depends_on", postgresql.UUID(),
                  sa.ForeignKey("arus_config.pipelines.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema="arus_config",
    )

    # ============ arus_config.pipeline_tables ============
    op.create_table(
        "pipeline_tables",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("pipeline_id", postgresql.UUID(),
                  sa.ForeignKey("arus_config.pipelines.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("source_table", sa.String(255), nullable=False),
        sa.Column("source_schema", sa.String(255), server_default="public"),
        sa.Column("sync_mode", sa.String(20), server_default="incremental"),
        sa.Column("watermark_column", sa.String(255), nullable=True),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true")),
        schema="arus_config",
    )

    # ============ arus_config.runtime_settings ============
    op.create_table(
        "runtime_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("key", sa.String(100), unique=True, nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema="arus_config",
    )

    # ============ arus_config.data_quality_log ============
    op.create_table(
        "data_quality_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("pipeline_id", postgresql.UUID(), nullable=False),
        sa.Column("run_id", postgresql.UUID(), nullable=False),
        sa.Column("table_name", sa.String(255), nullable=False),
        sa.Column("check_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("rows_extracted", sa.Integer(), nullable=True),
        sa.Column("rows_loaded", sa.Integer(), nullable=True),
        sa.Column("discrepancy_pct", sa.Float(), nullable=True),
        sa.Column("null_columns", sa.Text(), nullable=True),
        sa.Column("required_columns", sa.Text(), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("passed", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("checked_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema="arus_config",
    )

    # ============ arus_state.watermarks ============
    op.create_table(
        "watermarks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("pipeline_id", postgresql.UUID(), nullable=False),
        sa.Column("source_table", sa.String(255), nullable=False),
        sa.Column("watermark_col", sa.String(255), nullable=True),
        sa.Column("watermark_value", sa.Text(), nullable=True),
        sa.Column("row_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("last_run_id", postgresql.UUID(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema="arus_state",
    )

    # ============ staging._dead_letters ============
    op.create_table(
        "_dead_letters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("source_name", sa.String(255), nullable=False),
        sa.Column("table_name", sa.String(255), nullable=False),
        sa.Column("run_id", postgresql.UUID(), nullable=False),
        sa.Column("row_data", postgresql.JSONB(), nullable=False),
        sa.Column("error_text", sa.Text(), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema="staging",
    )

    # ============ arus_run_logs.runs ============
    op.create_table(
        "runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("pipeline_id", postgresql.UUID(), nullable=False),
        sa.Column("status", sa.String(20), server_default="running"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("trigger_type", sa.String(20), server_default="scheduled"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema="arus_run_logs",
    )

    # ============ arus_run_logs.run_table_stats ============
    op.create_table(
        "run_table_stats",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("run_id", postgresql.UUID(),
                  sa.ForeignKey("arus_run_logs.runs.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("table_name", sa.String(255), nullable=False),
        sa.Column("rows_extracted", sa.Integer(), server_default=sa.text("0")),
        sa.Column("rows_loaded_raw", sa.Integer(), server_default=sa.text("0")),
        sa.Column("rows_loaded_analytics", sa.Integer(), server_default=sa.text("0")),
        sa.Column("rows_failed", sa.Integer(), server_default=sa.text("0")),
        sa.Column("watermark_before", sa.Text(), nullable=True),
        sa.Column("watermark_after", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), server_default=sa.text("0")),
        sa.Column("error_message", sa.Text(), nullable=True),
        schema="arus_run_logs",
    )

    # ============ arus_run_logs.run_logs ============
    op.create_table(
        "run_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("run_id", postgresql.UUID(),
                  sa.ForeignKey("arus_run_logs.runs.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("level", sa.String(10), server_default="INFO"),
        sa.Column("message", sa.Text(), nullable=False),
        schema="arus_run_logs",
    )

    # ============ INDEXES ============
    op.create_index("idx_dead_letters_run_id", "_dead_letters", ["run_id"], schema="staging")
    op.create_index("idx_data_quality_run_id", "data_quality_log", ["run_id"], schema="arus_config")
    op.create_index("idx_data_quality_pipeline_id", "data_quality_log", ["pipeline_id"], schema="arus_config")


def downgrade() -> None:
    """Drop all tables and schemas."""
    tables = [
        ("arus_run_logs", "run_logs"),
        ("arus_run_logs", "run_table_stats"),
        ("arus_run_logs", "runs"),
        ("staging", "_dead_letters"),
        ("arus_state", "watermarks"),
        ("arus_config", "data_quality_log"),
        ("arus_config", "runtime_settings"),
        ("arus_config", "pipeline_tables"),
        ("arus_config", "pipelines"),
        ("arus_config", "destinations"),
        ("arus_config", "sources"),
        ("arus_config", "users"),
    ]
    for schema, table in reversed(tables):
        op.drop_table(table, schema=schema, if_exists=True)
