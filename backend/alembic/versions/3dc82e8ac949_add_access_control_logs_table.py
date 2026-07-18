"""add access_control_logs table

Revision ID: 3dc82e8ac949
Revises: 621c123f4aa9
Create Date: 2026-07-16 21:55:23.173919

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '3dc82e8ac949'
down_revision: Union[str, None] = '621c123f4aa9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'access_control_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('target_account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('target_account_type', sa.String(10), nullable=False),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('action_type', sa.String(10), nullable=False),
        sa.Column('reason', sa.String(200), nullable=True),
        sa.Column('acted_at', sa.String(14), nullable=False),
        sa.Column('acted_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('access_control_logs')
