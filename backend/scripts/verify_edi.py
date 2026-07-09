#!/usr/bin/env python3
"""EDI(SAM) 파일 주요 필드 검증 스크립트.

HIRA 별첨1(전자문서 교환방식/EDI) 레이아웃 기준 (2026-07-09 재작성).
레코드별 길이가 전부 달라(2096/325/43/75/739) 길이만으로 레코드 종류를
판별할 수 있다. 레코드 2~4는 모두 청구번호(10)+명세서일련번호(5)로 시작한다.

사용법:
    python scripts/verify_edi.py claim_xxxxx_TEST.sam
"""

import sys
from pathlib import Path

_RECORD_LENGTHS = {
    2096: "레코드1 (심사청구서 헤더)",
    325: "레코드2 (한방 명세서 일반내역)",
    43: "레코드2-1 (한방 명세서 상병내역)",
    75: "레코드3 (한방 명세서 진료내역)",
    739: "레코드4 (명세서 특정내역기재란)",
}


def _f(line: bytes, start: int, end: int) -> str:
    """1-indexed [start, end] 구간을 EUC-KR로 디코드해 반환 (양끝 포함)."""
    return line[start - 1:end].decode("euc-kr", errors="replace")


def _check(label: str, value: str) -> None:
    icon = "✅" if value.strip() and value.strip() != "0" * len(value.strip()) else "⚠️ "
    print(f"  {icon} {label}: {value!r}")


def verify(path: str) -> None:
    data = Path(path).read_bytes()
    lines = [l for l in data.split(b"\r\n") if l]
    if not lines:
        print("❌ 파일이 비어 있습니다.")
        return

    print(f"총 레코드 수: {len(lines)}")
    print()

    for line in lines:
        kind = _RECORD_LENGTHS.get(len(line))
        if kind is None:
            print(f"❌ 알 수 없는 레코드 길이: {len(line)} bytes — {line[:20]!r}...")
            continue

        if len(line) == 2096:
            print("=" * 50)
            print(f"{kind}")
            print("=" * 50)
            _check("청구서서식버전 (1-3)", _f(line, 1, 3))
            _check("명세서서식버전 (4-6)", _f(line, 4, 6))
            _check("청구번호       (7-16)", _f(line, 7, 16))
            _check("서식번호       (17-20)", _f(line, 17, 20))
            _check("요양기관기호   (21-28)", _f(line, 21, 28))
            _check("보험자종별구분 (30)", _f(line, 30, 30))
            _check("진료년월       (36-41)", _f(line, 36, 41))
            _check("청구일자       (246-253)", _f(line, 246, 253))
            _check("청구인         (254-273)", _f(line, 254, 273))

            writer = _f(line, 274, 293).strip()
            if writer == "상시점검":
                print(f"  ✅ 작성자성명   (274-293): 「{writer}」 — 테스트 모드 확인")
            elif writer:
                print(f"  ✅ 작성자성명   (274-293): {writer}")
            else:
                print("  ⚠️  작성자성명   (274-293): (비어 있음)")

            _check("건수           (42-47)", _f(line, 42, 47))
            _check("요양급여비용총액1 (48-59)", _f(line, 48, 59))
            _check("본인일부부담금 (60-71)", _f(line, 60, 71))
            _check("청구액         (84-95)", _f(line, 84, 95))
            print()

        elif len(line) == 325:
            print(f"{kind}")
            _check("  청구번호       (1-10)", _f(line, 1, 10))
            _check("  명세서일련번호 (11-15)", _f(line, 11, 15))
            _check("  서식번호       (16-19)", _f(line, 16, 19))
            _check("  요양기관기호   (20-27)", _f(line, 20, 27))
            _check("  요양급여비용총액1 (176-185)", _f(line, 176, 185))
            print()

        elif len(line) == 43:
            print(f"{kind}")
            _check("  명세서일련번호 (11-15)", _f(line, 11, 15))
            _check("  상병분류기호   (17-22)", _f(line, 17, 22))
            _check("  진료과목       (23-24)", _f(line, 23, 24))
            print()

        elif len(line) == 75:
            print(f"{kind}")
            _check("  명세서일련번호 (11-15)", _f(line, 11, 15))
            _check("  항번호/목번호  (16-19)", _f(line, 16, 19))
            _check("  줄번호         (20-23)", _f(line, 20, 23))
            _check("  코드           (25-33)", _f(line, 25, 33))
            _check("  금액           (56-65)", _f(line, 56, 65))
            print()

        elif len(line) == 739:
            special_code = _f(line, 35, 39).strip()
            content = _f(line, 40, 739).strip()
            print(f"  → {kind} [{special_code}]: {content[:60]!r}")

    print()
    print("검증 완료.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python scripts/verify_edi.py <파일경로>")
        sys.exit(1)
    verify(sys.argv[1])
