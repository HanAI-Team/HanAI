from datetime import datetime, timezone
from uuid import UUID

import pytest_asyncio

from app.auth.service import create_access_token
from app.core.models import Doctor, Hospital


@pytest_asyncio.fixture
async def associate_doctor(db, approved_doctor):
    owner, _ = approved_doctor
    doctor = Doctor(
        hospital_id=owner.hospital_id,
        name="부원장",
        license_number="11112222",
        password_hash="hashed_password",
        role="associate",
        is_approved=True,
        approved_at=datetime.now(timezone.utc),
    )
    db.add(doctor)
    await db.commit()
    await db.refresh(doctor)

    token = create_access_token(
        UUID(str(doctor.id)), UUID(str(doctor.hospital_id)), "associate"
    )
    return doctor, {"Authorization": f"Bearer {token}"}


async def test_patch_hospital_by_owner(client, approved_doctor):
    doctor, headers = approved_doctor

    resp = await client.patch(
        f"/api/hospitals/{doctor.hospital_id}",
        json={"name": "수정된병원", "institution_code": "12345678"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "수정된병원"
    assert data["institution_code"] == "12345678"


async def test_patch_hospital_only_updates_provided_fields(client, approved_doctor):
    doctor, headers = approved_doctor

    resp = await client.patch(
        f"/api/hospitals/{doctor.hospital_id}",
        json={"phone": "02-1234-5678"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["phone"] == "02-1234-5678"
    assert data["name"] == "테스트의원"


async def test_patch_hospital_rejects_non_owner(client, associate_doctor):
    doctor, headers = associate_doctor

    resp = await client.patch(
        f"/api/hospitals/{doctor.hospital_id}",
        json={"name": "권한없음"},
        headers=headers,
    )
    assert resp.status_code == 403


async def test_patch_hospital_rejects_other_hospital(client, approved_doctor, db):
    _, headers = approved_doctor

    other_hospital = Hospital(name="다른병원")
    db.add(other_hospital)
    await db.commit()
    await db.refresh(other_hospital)

    resp = await client.patch(
        f"/api/hospitals/{other_hospital.id}",
        json={"name": "침해시도"},
        headers=headers,
    )
    assert resp.status_code == 404


# ── 요양기관기호 형식 검증 (2026-07-16 추가) ──────────────────────────────
# SAM/EDI/처방전 생성이 이 값에 의존하는데, 기존엔 서버쪽 형식 검증이
# 전혀 없어 프론트 정규식만 우회하면(직접 API 호출 등) 깨진 값이 그대로
# 저장될 수 있었다. 실제로 DB의 병원 4곳 전부 이 값이 비어있는 채로
# 방치돼 있던 걸 계기로 서버쪽 검증을 추가했다.

async def test_요양기관기호_8자리_숫자_아니면_거부(client, approved_doctor):
    doctor, headers = approved_doctor

    resp = await client.patch(
        f"/api/hospitals/{doctor.hospital_id}",
        json={"institution_code": "123"},
        headers=headers,
    )
    assert resp.status_code == 422


async def test_요양기관기호_숫자아닌문자_포함시_거부(client, approved_doctor):
    doctor, headers = approved_doctor

    resp = await client.patch(
        f"/api/hospitals/{doctor.hospital_id}",
        json={"institution_code": "1234567A"},
        headers=headers,
    )
    assert resp.status_code == 422


async def test_요양기관기호_빈문자열로_비우기_시도시_거부(client, approved_doctor):
    """이미 설정된 요양기관기호를 빈 문자열로 지우려는 시도도 막는다
    (한 번 채워지면 실수로 비워질 수 없도록)."""
    doctor, headers = approved_doctor
    await client.patch(
        f"/api/hospitals/{doctor.hospital_id}",
        json={"institution_code": "12345678"},
        headers=headers,
    )

    resp = await client.patch(
        f"/api/hospitals/{doctor.hospital_id}",
        json={"institution_code": ""},
        headers=headers,
    )
    assert resp.status_code == 422


async def test_요양기관기호_생략하면_기존값_유지(client, approved_doctor):
    """institution_code 필드 자체를 안 보내면(부분 업데이트) 기존 값을 그대로 둔다."""
    doctor, headers = approved_doctor
    await client.patch(
        f"/api/hospitals/{doctor.hospital_id}",
        json={"institution_code": "12345678"},
        headers=headers,
    )

    resp = await client.patch(
        f"/api/hospitals/{doctor.hospital_id}",
        json={"phone": "02-0000-0000"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["institution_code"] == "12345678"


# ── 소프트웨어 승인번호 저장 후 새로고침 시 사라지는 버그 재현 (2026-07-22) ──
# PATCH /api/hospitals/{id}로 저장은 되지만(HospitalResponse에 approval_no
# 포함), 새로고침 시 프론트가 호출하는 GET /api/auth/me 응답에는
# approval_no가 아예 빠져있어 화면에서 값이 사라진 것처럼 보였다.

async def test_소프트웨어_승인번호_저장후_me_조회에도_반영(client, approved_doctor):
    doctor, headers = approved_doctor

    patch_resp = await client.patch(
        f"/api/hospitals/{doctor.hospital_id}",
        json={"approval_no": "TEST-2026-0001"},
        headers=headers,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["approval_no"] == "TEST-2026-0001"

    me_resp = await client.get("/api/auth/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["approval_no"] == "TEST-2026-0001"
