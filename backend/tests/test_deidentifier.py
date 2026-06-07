from app.pipeline.deidentifier import deidentifier


def test_주민번호_마스킹():
    result = deidentifier.process("환자 주민번호는 901225-1234567입니다.")
    assert "901225-1234567" not in result.cleaned
    assert "[주민번호]" in result.cleaned


def test_휴대폰번호_마스킹():
    result = deidentifier.process("연락처는 010-1234-5678입니다.")
    assert "010-1234-5678" not in result.cleaned
    assert "[연락처]" in result.cleaned


def test_일반전화번호_마스킹():
    result = deidentifier.process("병원 전화번호는 02-1234-5678입니다.")
    assert "02-1234-5678" not in result.cleaned
    assert "[연락처]" in result.cleaned


def test_이메일_마스킹():
    result = deidentifier.process("이메일은 hong@example.com 입니다.")
    assert "hong@example.com" not in result.cleaned
    assert "[이메일]" in result.cleaned


def test_이름과_호칭_마스킹():
    result = deidentifier.process("홍길동 님 들어오세요.")
    assert "홍길동" not in result.cleaned
    assert "[환자]" in result.cleaned


def test_환자_뒤_이름_마스킹():
    result = deidentifier.process("환자 김철수 분 들어오세요.")
    assert "[이름]" in result.cleaned


def test_생년월일_마스킹():
    result = deidentifier.process("생년월일은 1990년 12월 25일생입니다.")
    assert "1990년 12월 25일생" not in result.cleaned
    assert "[생년월일]" in result.cleaned


def test_주소_마스킹():
    result = deidentifier.process("환자분 주소는 서울특별시 강남구입니다.")
    assert "강남구" not in result.cleaned
    assert "[주소]" in result.cleaned


def test_차트번호_마스킹():
    result = deidentifier.process("차트번호 12345 확인해주세요.")
    assert "차트번호 12345" not in result.cleaned
    assert "[차트번호]" in result.cleaned


def test_직업_호칭은_마스킹되지_않음():
    result = deidentifier.process("원장님이 진료를 보십니다.")
    assert "원장님" in result.cleaned
    assert "[환자]" not in result.cleaned


def test_조사가_붙은_호칭도_보호됨():
    result = deidentifier.process("어머님께서 한의사님이 처방한 약을 드셨습니다.")
    assert "어머님께서" in result.cleaned
    assert "한의사님이" in result.cleaned
    assert "[환자]" not in result.cleaned


def test_개인정보_없으면_그대로():
    text = "어깨가 결리고 허리도 아픕니다."
    result = deidentifier.process(text)
    assert result.cleaned == text
    assert result.removed_items == []


def test_빈_문자열_처리():
    result = deidentifier.process("")
    assert result.cleaned == ""
    assert result.removed_items == []
