"""add performed_by_doctor_id to claim_line_items

Revision ID: ffe21842956a
Revises: bf74d65af763
Create Date: 2026-07-22 22:50:17.494344

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'ffe21842956a'
down_revision: Union[str, None] = 'bf74d65af763'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('claim_line_items', sa.Column('performed_by_doctor_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        'claim_line_items_performed_by_doctor_id_fkey',
        'claim_line_items', 'doctors', ['performed_by_doctor_id'], ['id'],
    )


def downgrade() -> None:
    op.drop_constraint('claim_line_items_performed_by_doctor_id_fkey', 'claim_line_items', type_='foreignkey')
    op.drop_column('claim_line_items', 'performed_by_doctor_id')
