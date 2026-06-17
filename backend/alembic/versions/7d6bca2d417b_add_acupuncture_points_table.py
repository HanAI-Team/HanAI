"""add_acupuncture_points_table

Revision ID: 7d6bca2d417b
Revises: aff8a9f436b0
Create Date: 2026-06-17 16:34:04.895916

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7d6bca2d417b'
down_revision: Union[str, None] = 'aff8a9f436b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'acupuncture_points',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('code', sa.String(length=10), nullable=False),
        sa.Column('korean_name', sa.String(length=50), nullable=False),
        sa.Column('meridian', sa.String(length=30), nullable=True),
        sa.Column('location', sa.Text(), nullable=True),
        sa.Column('is_standalone', sa.Boolean(), nullable=False, server_default='false'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
    )
    op.create_index('ix_acupuncture_points_code', 'acupuncture_points', ['code'])


def downgrade() -> None:
    op.drop_index('ix_acupuncture_points_code', table_name='acupuncture_points')
    op.drop_table('acupuncture_points')
