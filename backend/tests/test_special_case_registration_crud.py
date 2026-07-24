from uuid import UUID

from sqlalchemy import select

from app.billing.service import resolve_active_special_code
from app.core.models import AuditLog, Hospital, Patient

REGISTRATION_DATA = {
    "special_code": "V193",
    "category": "암",
    "registered_disease_code": "C169",
    "registration_number": "1-26-00000001",
    "registered_at": "2026-01-01",
}


async def _create_patient(client, headers) -> str:
    resp = await client.post(
        "/api/patients/register", json={"name": "산정특례환자", "gender": "남"}, headers=headers
    )
    return resp.json()["id"]


async def test_산정특례_등록_생성(client, approved_doctor):
    _, headers = approved_doctor
    patient_id = await _create_patient(client, headers)

    resp = await client.post(
        f"/api/patients/{patient_id}/special-case-registrations",
        json=REGISTRATION_DATA,
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["special_code"] == "V193"
    assert data["category"] == "암"
    assert data["registered_disease_code"] == "C169"
    assert data["registration_number"] == "1-26-00000001"
    assert data["status"] == "active"


async def test_산정특례_등록_목록_조회(client, approved_doctor):
    _, headers = approved_doctor
    patient_id = await _create_patient(client, headers)

    await client.post(
        f"/api/patients/{patient_id}/special-case-registrations",
        json=REGISTRATION_DATA,
        headers=headers,
    )

    resp = await client.get(
        f"/api/patients/{patient_id}/special-case-registrations", headers=headers
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["special_code"] == "V193"


async def test_산정특례_등록_수정(client, approved_doctor):
    _, headers = approved_doctor
    patient_id = await _create_patient(client, headers)

    create_resp = await client.post(
        f"/api/patients/{patient_id}/special-case-registrations",
        json=REGISTRATION_DATA,
        headers=headers,
    )
    registration_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/patients/{patient_id}/special-case-registrations/{registration_id}",
        json={"expires_at": "2027-01-01"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["expires_at"] == "2027-01-01"
    assert data["special_code"] == "V193"  # 변경 안 한 필드는 유지


async def test_산정특례_등록_비활성화(client, approved_doctor, db):
    _, headers = approved_doctor
    patient_id = await _create_patient(client, headers)

    create_resp = await client.post(
        f"/api/patients/{patient_id}/special-case-registrations",
        json=REGISTRATION_DATA,
        headers=headers,
    )
    registration_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/patients/{patient_id}/special-case-registrations/{registration_id}/deactivate",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"

    # 비활성화 후에는 본인부담률 계산에서 제외되어야 함
    result = await resolve_active_special_code(db, UUID(patient_id))
    assert result.special_code is None


async def test_산정특례_등록_다른병원_환자_접근시_404(client, approved_doctor, db):
    _, headers = approved_doctor

    other_hospital = Hospital(name="다른병원")
    db.add(other_hospital)
    await db.flush()
    other_patient = Patient(hospital_id=other_hospital.id, name="다른병원환자", gender="여")
    db.add(other_patient)
    await db.commit()
    await db.refresh(other_patient)

    resp = await client.post(
        f"/api/patients/{other_patient.id}/special-case-registrations",
        json=REGISTRATION_DATA,
        headers=headers,
    )
    assert resp.status_code == 404


async def test_산정특례_등록_감사로그_기록(client, approved_doctor, db):
    doctor, headers = approved_doctor
    patient_id = await _create_patient(client, headers)

    create_resp = await client.post(
        f"/api/patients/{patient_id}/special-case-registrations",
        json=REGISTRATION_DATA,
        headers=headers,
    )
    registration_id = create_resp.json()["id"]

    await client.patch(
        f"/api/patients/{patient_id}/special-case-registrations/{registration_id}",
        json={"expires_at": "2027-01-01"},
        headers=headers,
    )
    await client.post(
        f"/api/patients/{patient_id}/special-case-registrations/{registration_id}/deactivate",
        headers=headers,
    )

    result = await db.execute(
        select(AuditLog).where(
            AuditLog.table_name == "special_case_registrations",
            AuditLog.record_id == registration_id,
        ).order_by(AuditLog.id)
    )
    logs = result.scalars().all()
    actions = [log.action for log in logs]
    assert actions == ["INSERT", "UPDATE", "DEACTIVATE"]
    assert all(log.actor_id == doctor.id for log in logs)


async def test_산정특례_특정기호_목록_조회(client, approved_doctor):
    """드롭다운용 특정기호 레퍼런스 목록 — V193(암)이 포함돼 있는지만 확인."""
    _, headers = approved_doctor

    resp = await client.get("/api/billing/special-case-codes", headers=headers)
    assert resp.status_code == 200
    codes = {item["code"] for item in resp.json()}
    assert "V193" in codes


# ── 이번 작업의 핵심: 등록 전/후 resolve_active_special_code() 반영 확인 ──


async def test_등록_전에는_일반요율_등록_후에는_산정특례요율_반영(client, approved_doctor, db):
    """등록 API를 실제로 호출하기 전에는 resolve_active_special_code()가
    special_code=None(일반요율)을 반환하고, API로 등록한 직후에는 해당
    특정기호가 즉시 반영되는지 하나의 환자에 대해 순서대로 확인한다."""
    _, headers = approved_doctor
    patient_id = await _create_patient(client, headers)

    before = await resolve_active_special_code(db, UUID(patient_id))
    assert before.special_code is None

    resp = await client.post(
        f"/api/patients/{patient_id}/special-case-registrations",
        json=REGISTRATION_DATA,
        headers=headers,
    )
    assert resp.status_code == 201

    after = await resolve_active_special_code(db, UUID(patient_id))
    assert after.special_code == "V193"
    assert after.review_reason is None


# ── 등록번호/사전승인번호 최소 형식 검증 (MT014, HIRA "9(20)": 숫자 최대 20자리) ──
# 정확한 자릿수(10/11/13/15/18)는 보험유형·등록유형(일반/틀니/임플란트)에 따라
# 갈리는데 이 구분이 시스템에 모델링돼 있지 않아 강제하지 않는다. 다만 기존
# 모델 주석("01-24-00012345")과 테스트 데이터(REGISTRATION_DATA의
# "1-26-00000001")가 이미 하이픈 포함 표기를 쓰고 있어, 숫자만 허용하면 기존
# 관례와 충돌한다 — 숫자+하이픈만 허용하고 하이픈 제외 자릿수만 20자로 제한한다.


async def test_등록번호_숫자와_하이픈만_있으면_통과(client, approved_doctor):
    _, headers = approved_doctor
    patient_id = await _create_patient(client, headers)

    resp = await client.post(
        f"/api/patients/{patient_id}/special-case-registrations",
        json={**REGISTRATION_DATA, "registration_number": "01-24-00012345"},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["registration_number"] == "01-24-00012345"


async def test_등록번호_문자_포함시_거부(client, approved_doctor):
    _, headers = approved_doctor
    patient_id = await _create_patient(client, headers)

    resp = await client.post(
        f"/api/patients/{patient_id}/special-case-registrations",
        json={**REGISTRATION_DATA, "registration_number": "V193abc"},
        headers=headers,
    )
    assert resp.status_code == 422


async def test_등록번호_하이픈_제외_21자리_이상이면_거부(client, approved_doctor):
    _, headers = approved_doctor
    patient_id = await _create_patient(client, headers)

    resp = await client.post(
        f"/api/patients/{patient_id}/special-case-registrations",
        json={**REGISTRATION_DATA, "registration_number": "1" * 21},
        headers=headers,
    )
    assert resp.status_code == 422


async def test_등록번호_생략하면_통과(client, approved_doctor):
    """registration_number는 선택 입력 필드이므로 아예 안 보내도 정상 등록된다."""
    _, headers = approved_doctor
    patient_id = await _create_patient(client, headers)

    data = {k: v for k, v in REGISTRATION_DATA.items() if k != "registration_number"}
    resp = await client.post(
        f"/api/patients/{patient_id}/special-case-registrations",
        json=data,
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["registration_number"] is None


async def test_사전승인번호도_동일한_형식_검증_적용(client, approved_doctor):
    """V810 전용 prior_approval_number도 MT014 공통 형식(숫자+하이픈)을 따른다."""
    _, headers = approved_doctor
    patient_id = await _create_patient(client, headers)

    resp = await client.post(
        f"/api/patients/{patient_id}/special-case-registrations",
        json={
            **REGISTRATION_DATA,
            "special_code": "V810",
            "category": "중증치매",
            "prior_approval_number": "1-26-00000001abc",
        },
        headers=headers,
    )
    assert resp.status_code == 422
