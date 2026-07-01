"""add_claim_resubmission_fields

Revision ID: e9f2c7a4b3d8
Revises: c4a8e2f9d1b6
Create Date: 2026-06-30 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e9f2c7a4b3d8'
down_revision: Union[str, None] = 'c4a8e2f9d1b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('claims', sa.Column('original_receipt_no', sa.Integer(), nullable=True))
    op.add_column('claims', sa.Column('original_record_serial', sa.Integer(), nullable=True))
    op.add_column('claims', sa.Column('rejection_reason_code', sa.String(length=2), nullable=True))

    op.create_table(
        'claim_resubmission_histories',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('claim_id', sa.UUID(), nullable=False),
        sa.Column('actor_id', sa.UUID(), nullable=True),
        sa.Column('claim_type', sa.String(), nullable=False),
        sa.Column('receipt_no', sa.Integer(), nullable=True),
        sa.Column('record_serial', sa.Integer(), nullable=True),
        sa.Column('reason_code', sa.String(length=2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['claim_id'], ['claims.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('claim_resubmission_histories')
    op.drop_column('claims', 'rejection_reason_code')
    op.drop_column('claims', 'original_record_serial')
    op.drop_column('claims', 'original_receipt_no')
