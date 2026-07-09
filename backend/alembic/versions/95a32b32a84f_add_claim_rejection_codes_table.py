"""add claim rejection codes table

Revision ID: 95a32b32a84f
Revises: fbc60a2cb18e
Create Date: 2026-07-10 06:26:15.039004

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '95a32b32a84f'
down_revision: Union[str, None] = 'fbc60a2cb18e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "claim_rejection_codes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("category", sa.String(length=10), nullable=False),
        sa.Column("code", sa.String(length=2), nullable=False),
        sa.Column("detail_code", sa.String(length=2), nullable=False, server_default=""),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("category", "code", "detail_code", name="uq_claim_rejection_code"),
    )


def downgrade() -> None:
    op.drop_table("claim_rejection_codes")
