
import sqlalchemy as sa
from alembic import op

revision = '20260623_fee_master'
down_revision = 'e5f6a1b2c3d4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # fee_master 테이블 생성 + 시딩
    op.create_table(
        "fee_master",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(10), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("fee", sa.Integer(), nullable=False),
        sa.Column("insurance_types", sa.String(10), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_fee_master_code", "fee_master", ["code"])

    op.execute("""
        INSERT INTO fee_master (code, name, category, fee, insurance_types) VALUES
        ('AA159', '체침', '침술', 6260, '4,5,7'),
        ('AA161', '전침', '침술', 8350, '4,5,7'),
        ('AA163', '도침(침도)', '침술', 12500, '4,5,7'),
        ('AA165', '화침', '침술', 9140, '4,5,7'),
        ('AA167', '수침(약침)', '침술', 10200, '4,5,7'),
        ('AA171', '뜸(단순)', '뜸', 4100, '4,5,7'),
        ('AA173', '뜸(복잡)', '뜸', 6150, '4,5,7'),
        ('AA211', '건부항(단순)', '부항', 3900, '4,5,7'),
        ('AA213', '건부항(복잡)', '부항', 5600, '4,5,7'),
        ('AA215', '습부항', '부항', 6700, '4,5,7'),
        ('NA161', '추나요법(경증)', '추나', 20060, '4,5'),
        ('NA162', '추나요법(중증)', '추나', 40120, '4,5')
    """)

    # medical_record_procedures에 FK 추가
    op.add_column(
        "medical_record_procedures",
        sa.Column("fee_master_code", sa.String(10), nullable=True),
    )
    op.create_foreign_key(
        "fk_procedures_fee_master",
        "medical_record_procedures",
        "fee_master",
        ["fee_master_code"],
        ["code"],
    )
    op.drop_column("medical_record_procedures", "procedure_code") 


def downgrade() -> None:
    op.add_column(
        "medical_record_procedures",
        sa.Column("procedure_code", sa.String(), nullable=True),  # 추가
    )
    op.drop_constraint("fk_procedures_fee_master", "medical_record_procedures", type_="foreignkey")
    op.drop_column("medical_record_procedures", "fee_master_code")
    op.drop_index("ix_fee_master_code", table_name="fee_master")
    op.drop_table("fee_master")