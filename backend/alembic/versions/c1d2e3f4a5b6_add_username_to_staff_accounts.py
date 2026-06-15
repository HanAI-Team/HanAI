"""add_username_to_staff_accounts

Revision ID: c1d2e3f4a5b6
Revises: 94cd73bd4fa2
Create Date: 2026-06-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, None] = '94cd73bd4fa2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('staff_accounts', sa.Column('username', sa.String(), nullable=True))
    op.execute('UPDATE staff_accounts SET username = email WHERE username IS NULL')
    op.alter_column('staff_accounts', 'username', nullable=False)
    op.create_unique_constraint('uq_staff_accounts_username', 'staff_accounts', ['username'])

    op.alter_column('staff_accounts', 'email', nullable=True)


def downgrade() -> None:
    op.alter_column('staff_accounts', 'email', nullable=False)
    op.drop_constraint('uq_staff_accounts_username', 'staff_accounts', type_='unique')
    op.drop_column('staff_accounts', 'username')
