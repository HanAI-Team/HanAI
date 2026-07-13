"""add agency_code approval_no to hospital and login_logs trigger

Revision ID: 5ef0afd54549
Revises: 37fb632f500f
Create Date: 2026-07-13 12:31:15.054246

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5ef0afd54549'
down_revision: Union[str, None] = '37fb632f500f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('hospitals', sa.Column('approval_no', sa.String(length=35), nullable=True))

    op.execute("""
        CREATE OR REPLACE FUNCTION protect_login_logs() RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'UPDATE' THEN
                RAISE EXCEPTION 'login_logs 레코드는 수정할 수 없습니다.';
            ELSIF TG_OP = 'DELETE' THEN
                IF OLD.attempted_at > NOW() - INTERVAL '2 years' THEN
                    RAISE EXCEPTION 'login_logs 보관기간(2년) 내 레코드는 삭제할 수 없습니다.';
                END IF;
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trg_protect_login_logs
        BEFORE UPDATE OR DELETE ON login_logs
        FOR EACH ROW EXECUTE FUNCTION protect_login_logs();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_protect_login_logs ON login_logs;")
    op.execute("DROP FUNCTION IF EXISTS protect_login_logs();")

    op.drop_column('hospitals', 'approval_no')
