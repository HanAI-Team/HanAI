"""add_audit_logs_table

Revision ID: aff8a9f436b0
Revises: ebd75a71b9bd
Create Date: 2026-06-17 16:21:49.985068

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aff8a9f436b0'
down_revision: Union[str, None] = 'ebd75a71b9bd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('table_name', sa.String(length=50), nullable=False),
        sa.Column('record_id', sa.String(length=36), nullable=False),
        sa.Column('action', sa.String(length=10), nullable=False),
        sa.Column('actor_id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('actor_type', sa.String(length=20), nullable=True),
        sa.Column('changed_at', sa.String(length=14), nullable=False),
        sa.Column('detail', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_audit_logs_table_record', 'audit_logs', ['table_name', 'record_id'])
    op.create_index('ix_audit_logs_changed_at', 'audit_logs', ['changed_at'])


def downgrade() -> None:
    op.drop_index('ix_audit_logs_changed_at', table_name='audit_logs')
    op.drop_index('ix_audit_logs_table_record', table_name='audit_logs')
    op.drop_table('audit_logs')
