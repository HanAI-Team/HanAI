"""add reception dashboard bed field and claim payments

Revision ID: 8fbcf6b41389
Revises: ab0a06e477f2
Create Date: 2026-07-14 10:09:39.958724

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '8fbcf6b41389'
down_revision: Union[str, None] = 'ab0a06e477f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("daily_queue", sa.Column("assigned_bed", sa.String(20), nullable=True))
    op.add_column(
        "daily_queue",
        sa.Column("claim_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("claims.id"), nullable=True),
    )

    op.create_table(
        "claim_payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "hospital_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("hospitals.id"), nullable=False,
        ),
        sa.Column(
            "claim_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("claims.id"), nullable=False,
        ),
        sa.Column("method", sa.String(20), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("processed_by_name", sa.String(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("claim_payments")
    op.drop_column("daily_queue", "claim_id")
    op.drop_column("daily_queue", "assigned_bed")
