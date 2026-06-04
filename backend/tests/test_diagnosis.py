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
