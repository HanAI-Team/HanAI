"""add drug master table

Revision ID: 8c1774fee41d
Revises: 95a32b32a84f
Create Date: 2026-07-10 06:58:34.439523

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8c1774fee41d'
down_revision: Union[str, None] = '95a32b32a84f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "drug_master",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("product_code", sa.String(length=20), nullable=False),
        sa.Column("product_name", sa.String(length=300), nullable=False),
        sa.Column("ingredient_code", sa.String(length=20), nullable=True),
        sa.Column("ingredient_name", sa.String(length=1500), nullable=True),
        sa.Column("company_name", sa.String(length=100), nullable=True),
        sa.Column("spec", sa.String(length=50), nullable=True),
        sa.Column("unit", sa.String(length=30), nullable=True),
        sa.Column("unit_price", sa.Integer(), nullable=False),
        sa.Column("administration_route", sa.String(length=20), nullable=True),
        sa.Column("classification_code", sa.String(length=10), nullable=True),
        sa.Column("is_prescription", sa.Boolean(), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_code"),
    )
    op.create_index(op.f("ix_drug_master_product_code"), "drug_master", ["product_code"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_drug_master_product_code"), table_name="drug_master")
    op.drop_table("drug_master")
