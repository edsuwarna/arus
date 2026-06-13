"""add rows_synced column to runs table

Revision ID: 010
Revises: 009
Create Date: 2026-06-13 00:40:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '010'
down_revision: Union[str, None] = '009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'runs',
        sa.Column('rows_synced', sa.Integer(), nullable=True, server_default=sa.text('0')),
        schema='arus_run_logs'
    )


def downgrade() -> None:
    op.drop_column('runs', 'rows_synced', schema='arus_run_logs')
