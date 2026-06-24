"""add_institution_code_and_patient_rrn

Revision ID: 74f41eb1009d
Revises: b272c577f245
Create Date: 2026-06-24 10:40:03.659866

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '74f41eb1009d'
down_revision: Union[str, None] = 'b272c577f245'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('hospitals', sa.Column('institution_code', sa.String(length=8), nullable=True))
    op.add_column('patients', sa.Column('rrn', sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column('hospitals', 'institution_code')
    op.drop_column('patients', 'rrn')
