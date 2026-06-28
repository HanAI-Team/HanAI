"""add_account_history_and_login_log

Revision ID: 26f8cde16f71
Revises: e7fdb3bcd41d
Create Date: 2026-06-26 21:03:10.027229

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '26f8cde16f71'
down_revision: Union[str, None] = 'e7fdb3bcd41d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('account_histories',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('account_type', sa.String(), nullable=False),
    sa.Column('account_id', sa.UUID(), nullable=False),
    sa.Column('action', sa.String(), nullable=False),
    sa.Column('actor_id', sa.UUID(), nullable=True),
    sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('detail', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('login_logs',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('account_type', sa.String(), nullable=False),
    sa.Column('account_id', sa.UUID(), nullable=True),
    sa.Column('success', sa.Boolean(), nullable=False),
    sa.Column('ip_address', sa.String(length=45), nullable=True),
    sa.Column('user_agent', sa.String(length=500), nullable=True),
    sa.Column('attempted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('login_logs')
    op.drop_table('account_histories')
