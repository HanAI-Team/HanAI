"""merge special_case_registrations and medical_aid_grade heads

Revision ID: e2f3a4b5c6d7
Revises: a3d7e2c9f6b1, c3d4e5f6a7b8
Create Date: 2026-07-07 10:00:00.000000

"""
from typing import Sequence, Union

revision: str = 'e2f3a4b5c6d7'
down_revision: Union[str, tuple] = ('a3d7e2c9f6b1', 'c3d4e5f6a7b8')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
