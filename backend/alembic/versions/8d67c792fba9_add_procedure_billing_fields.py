"""add_procedure_billing_fields

Revision ID: 8d67c792fba9
Revises: 3d20d6824663
Create Date: 2026-06-23 14:16:29.983921

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '8d67c792fba9'
down_revision: Union[str, None] = '3d20d6824663'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('medical_record_procedures', sa.Column('prescription_days', sa.Integer(), nullable=True))
    op.add_column('medical_record_procedures', sa.Column('copay_rate_code', sa.String(length=2), nullable=True))
    op.add_column('medical_record_procedures', sa.Column('prescription_issue_date', sa.String(length=8), nullable=True))
    op.add_column('medical_record_procedures', sa.Column('prescription_serial', sa.Integer(), nullable=True))
    op.add_column('medical_record_procedures', sa.Column('adjustment_type', sa.String(length=10), nullable=True))


def downgrade() -> None:
    op.drop_column('medical_record_procedures', 'adjustment_type')
    op.drop_column('medical_record_procedures', 'prescription_serial')
    op.drop_column('medical_record_procedures', 'prescription_issue_date')
    op.drop_column('medical_record_procedures', 'copay_rate_code')
    op.drop_column('medical_record_procedures', 'prescription_days')
