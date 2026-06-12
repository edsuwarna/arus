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
    # Column was already renamed in a previous deployment
    pass


def downgrade() -> None:
    pass
