"""next_claim_serial() — 청구번호 뒷자리 4자리 일련번호를 병원+진료년월
조합별로 원자적으로 증가시키는 카운터 테스트.

2026-07-16: 청구번호가 항상 "0001"로 고정돼 있어 같은 달에 보완·추가청구
재전송이나 상시점검 재시험으로 여러 번 청구서를 만들면 번호가 겹치는
문제가 있어 도입.
"""

from app.billing.service import next_claim_serial


async def test_같은_병원_같은_달이면_호출할때마다_1씩_증가(db, approved_doctor):
    doctor, _ = approved_doctor
    s1 = await next_claim_serial(db, doctor.hospital_id, 2026, 7)
    s2 = await next_claim_serial(db, doctor.hospital_id, 2026, 7)
    s3 = await next_claim_serial(db, doctor.hospital_id, 2026, 7)
    assert (s1, s2, s3) == (1, 2, 3)


async def test_다른_진료년월은_독립적으로_1부터_시작(db, approved_doctor):
    doctor, _ = approved_doctor
    await next_claim_serial(db, doctor.hospital_id, 2026, 7)
    await next_claim_serial(db, doctor.hospital_id, 2026, 7)

    s_aug = await next_claim_serial(db, doctor.hospital_id, 2026, 8)
    assert s_aug == 1


async def test_다른_병원은_독립적으로_1부터_시작(db, approved_doctor):
    from app.core.models import Hospital

    doctor, _ = approved_doctor
    await next_claim_serial(db, doctor.hospital_id, 2026, 7)
    await next_claim_serial(db, doctor.hospital_id, 2026, 7)

    other_hospital = Hospital(name="다른병원")
    db.add(other_hospital)
    await db.commit()
    await db.refresh(other_hospital)

    s_other = await next_claim_serial(db, other_hospital.id, 2026, 7)
    assert s_other == 1
