"""add_fee_master_code_to_procedures

Revision ID: 3d20d6824663
Revises: f1a2b3c4d5e6
Create Date: 2026-06-23 13:34:49.580559

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '3d20d6824663'
down_revision: Union[str, None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('medical_record_procedures', sa.Column('fee_master_code', sa.String(length=20), nullable=True))
    op.create_foreign_key(
        'fk_medical_record_procedures_fee_master_code',
        'medical_record_procedures', 'fee_master', ['fee_master_code'], ['code'],
    )


def downgrade() -> None:
    op.drop_constraint('fk_medical_record_procedures_fee_master_code', 'medical_record_procedures', type_='foreignkey')
    op.drop_column('medical_record_procedures', 'fee_master_code')
