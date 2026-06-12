"""Add MongoDB-specific columns to sources table.

Revision ID: 002_add_mongo_source_fields
Revises: 001_initial
Create Date: 2025-06-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002_add_mongo_source_fields"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sources",
        sa.Column("uri", sa.Text(), nullable=True),
        schema="arus_config",
    )
    op.add_column(
        "sources",
        sa.Column("auth_source", sa.String(100), nullable=True),
        schema="arus_config",
    )


def downgrade() -> None:
    op.drop_column("sources", "auth_source", schema="arus_config")
    op.drop_column("sources", "uri", schema="arus_config")
