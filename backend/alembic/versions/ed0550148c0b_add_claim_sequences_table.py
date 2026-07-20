"""add claim sequences table

Revision ID: ed0550148c0b
Revises: a8ae7437bc51
Create Date: 2026-07-16 08:16:16.444344

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'ed0550148c0b'
down_revision: Union[str, None] = '3dc82e8ac949'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "claim_sequences",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "hospital_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("hospitals.id"), nullable=False,
        ),
        sa.Column("claim_period_year", sa.Integer(), nullable=False),
        sa.Column("claim_period_month", sa.Integer(), nullable=False),
        sa.Column("last_serial", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint(
            "hospital_id", "claim_period_year", "claim_period_month",
            name="uq_claim_sequence_hospital_period",
        ),
    )


def downgrade() -> None:
    op.drop_table("claim_sequences")
