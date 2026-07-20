"""add_claim_review_results

Revision ID: l5m6n7o8p9q0
Revises: 95f4633f4e19
Create Date: 2026-07-20 00:00:00.000000

심평원 심사결과(수신) 수동 업로드용 테이블. 실연동 전까지 CSV 업로드로 채운다.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "l5m6n7o8p9q0"
down_revision: Union[str, None] = "95f4633f4e19"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "claim_review_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("hospital_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("claim_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("receipt_number", sa.String(), nullable=False),
        sa.Column("review_type", sa.String(), nullable=False),
        sa.Column("result_code", sa.String(), nullable=False),
        sa.Column("original_amount", sa.Integer(), nullable=False),
        sa.Column("approved_amount", sa.Integer(), nullable=False),
        sa.Column("reduced_amount", sa.Integer(), nullable=False),
        sa.Column("reduce_reason", sa.Text(), nullable=True),
        sa.Column("review_date", sa.Date(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("raw_content", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["hospital_id"], ["hospitals.id"]),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_claim_review_results_hospital_id", "claim_review_results", ["hospital_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_claim_review_results_hospital_id", table_name="claim_review_results")
    op.drop_table("claim_review_results")
