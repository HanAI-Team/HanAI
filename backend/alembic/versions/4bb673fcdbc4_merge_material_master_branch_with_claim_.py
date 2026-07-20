"""merge material_master branch with claim_review_results/billing_agent branch

Revision ID: 4bb673fcdbc4
Revises: aa00ecf812c3, n7o8p9q0r1s2
Create Date: 2026-07-21 08:08:59.055300

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4bb673fcdbc4'
down_revision: Union[str, None] = ('aa00ecf812c3', 'n7o8p9q0r1s2')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
