"""add_password_policy

Revision ID: b0247c27c0b1
Revises: 26f8cde16f71
Create Date: 2026-06-26 21:03:43.450344

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b0247c27c0b1'
down_revision: Union[str, None] = '26f8cde16f71'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('password_histories',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('account_type', sa.String(), nullable=False),
    sa.Column('account_id', sa.UUID(), nullable=False),
    sa.Column('password_hash', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column('doctors', sa.Column('password_changed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('doctors', sa.Column('force_password_change', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('staff_accounts', sa.Column('password_changed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('staff_accounts', sa.Column('force_password_change', sa.Boolean(), server_default='false', nullable=False))


def downgrade() -> None:
    op.drop_column('staff_accounts', 'force_password_change')
    op.drop_column('staff_accounts', 'password_changed_at')
    op.drop_column('doctors', 'force_password_change')
    op.drop_column('doctors', 'password_changed_at')
    op.drop_table('password_histories')
