"""add data_download_logs

Revision ID: d46f8556a759
Revises: 133468ec66c3
Create Date: 2026-07-10 16:06:11.182911

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd46f8556a759'
down_revision: Union[str, None] = '133468ec66c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('data_download_logs',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('hospital_id', sa.UUID(), nullable=False),
    sa.Column('doctor_id', sa.UUID(), nullable=True),
    sa.Column('download_type', sa.String(length=50), nullable=False),
    sa.Column('reason', sa.String(length=500), nullable=False),
    sa.Column('ip_address', sa.String(length=45), nullable=True),
    sa.Column('downloaded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['hospital_id'], ['hospitals.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('data_download_logs')
