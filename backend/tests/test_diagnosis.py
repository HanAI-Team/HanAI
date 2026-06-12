from app.diagnosis.anonymize import anonymize


def test_주민번호_마스킹():
    result = anonymize("환자 주민번호는 901225-1234567입니다.")
    assert "901225-1234567" not in result
    assert "[주민번호]" in result


def test_전화번호_마스킹():
    result = anonymize("연락처: 010-1234-5678")
    assert "010-1234-5678" not in result
    assert "[연락처]" in result


def test_이메일_마스킹():
    result = anonymize("이메일은 hong@example.com 입니다.")
    assert "hong@example.com" not in result
    assert "[이메일]" in result


def test_이름_마스킹():
    result = anonymize("홍길동 님 안녕하세요.")
    assert "홍길동" not in result
    assert "[환자]" in result


def test_개인정보_없으면_그대로():
    text = "머리가 아프고 지끈지끈합니다."
    assert anonymize(text) == text


async def test_diagnose_text_정상_응답(client, approved_doctor, monkeypatch):
    _, headers = approved_doctor

    async def _mock_diagnose(text):
        return {"dataset_based": {}, "claude_based": {}}

    monkeypatch.setattr("app.diagnosis.service.diagnose", _mock_diagnose)

    resp = await client.post(
        "/api/diagnosis/",
        json={"transcription": "두통이 있습니다"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["result"] == {"dataset_based": {}, "claude_based": {}}


async def test_public_ask_로그인_없이_응답(client, monkeypatch):
    async def _fake_stream(question):
        for chunk in ["답변", "입니다"]:
            yield chunk

    monkeypatch.setattr("app.diagnosis.service.run_ask_stream", _fake_stream)

    resp = await client.post(
        "/api/diagnosis/public-ask",
        json={"question": "소음인 소화불량에 좋은 처방은?"},
    )
    assert resp.status_code == 200
    assert resp.text == "답변입니다"


async def test_diagnose_text_medical_history_포함됨(client, approved_doctor, monkeypatch):
    _, headers = approved_doctor
    received = {}

    async def _mock_diagnose(text):
        received["text"] = text
        return {"dataset_based": {}, "claude_based": {}}

    monkeypatch.setattr("app.diagnosis.service.diagnose", _mock_diagnose)

    resp = await client.post(
        "/api/diagnosis/",
        json={
            "transcription": "두통이 있습니다",
            "medical_history": "고혈압 약 복용 중",
        },
        headers=headers,
    )
    assert resp.status_code == 200
    assert "고혈압" in received["text"]
