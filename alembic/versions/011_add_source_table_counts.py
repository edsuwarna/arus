"""add table_count and enabled_table_count columns to sources table

Revision ID: 011
Revises: 010
Create Date: 2026-06-16 10:45:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '011'
down_revision: Union[str, None] = '010'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'sources',
        sa.Column('table_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        schema='arus_config'
    )
    op.add_column(
        'sources',
        sa.Column('enabled_table_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        schema='arus_config'
    )


def downgrade() -> None:
    op.drop_column('sources', 'table_count', schema='arus_config')
    op.drop_column('sources', 'enabled_table_count', schema='arus_config')
