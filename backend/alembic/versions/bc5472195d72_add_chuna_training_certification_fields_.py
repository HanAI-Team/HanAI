"""add chuna training certification fields to doctors

Revision ID: bc5472195d72
Revises: 061e391d28ec
Create Date: 2026-07-08 17:35:50.953336

이 파일은 `alembic revision --autogenerate`가 자동 생성한 원본에서
Doctor.chuna_training_certified / chuna_training_banner_seen 컬럼 추가
2줄만 남기고 나머지는 전부 제거했습니다 (2026-07-08, 승원 확인).

제거한 것: refresh_token 테이블 삭제, acupuncture_points/medical_record_procedures의
JSONB→JSON 타입 변경, claim_line_items FK 재생성(ondelete 옵션 차이),
claims/audit_logs/medical_records의 인덱스 삭제, fee_master/kcd_u_codes/
acupuncture_points의 unique 제약 변경 등 — 이건 모델(models.py)과 실제 DB
사이에 누적된 스키마 드리프트를 autogenerate가 통째로 잡아낸 것으로,
이번 작업(사전교육 이수여부 필드 추가) 범위 밖입니다. 별도로 태균과
협의해서 처리할 사항이라 이 마이그레이션에는 포함하지 않았습니다.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'bc5472195d72'
down_revision: Union[str, None] = '061e391d28ec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('doctors', sa.Column('chuna_training_certified', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('doctors', sa.Column('chuna_training_banner_seen', sa.Boolean(), server_default='false', nullable=False))


def downgrade() -> None:
    op.drop_column('doctors', 'chuna_training_banner_seen')
    op.drop_column('doctors', 'chuna_training_certified')
