import base64
import logging
import re
from datetime import date

import httpx
from app.core.config import settings
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

logger = logging.getLogger(__name__)

# 주민번호 7번째 자리(성별 코드) -> 출생 세기
_BIRTH_CENTURY_BY_GENDER_DIGIT = {
    "9": 1800, "0": 1800,
    "1": 1900, "2": 1900, "5": 1900, "6": 1900,
    "3": 2000, "4": 2000, "7": 2000, "8": 2000,
}


def extract_birth_date(jumin: str, *, callback_id: str | None = None) -> date | None:
    """주민번호 앞 6자리(YYMMDD)+7번째 자리(성별 코드)로 생년월일을 계산한다.
    형식이 맞지 않으면 None을 반환한다 (호출부는 회원가입을 막지 않고 birth_date만 비워둔다).
    실패 시 사유와 callback_id만 로그로 남기고 jumin 원본은 절대 남기지 않는다."""
    digits = re.sub(r"\D", "", jumin)
    if len(digits) < 7:
        logger.warning(
            "생년월일 파싱 실패: 자릿수 부족 (callback_id=%s)", callback_id
        )
        return None

    century = _BIRTH_CENTURY_BY_GENDER_DIGIT.get(digits[6])
    if century is None:
        logger.warning(
            "생년월일 파싱 실패: 성별 코드 인식 불가 (callback_id=%s)", callback_id
        )
        return None

    yy, mm, dd = digits[0:2], digits[2:4], digits[4:6]
    try:
        return date(century + int(yy), int(mm), int(dd))
    except ValueError:
        logger.warning(
            "생년월일 파싱 실패: 날짜 형식 무효 (callback_id=%s)", callback_id
        )
        return None

_INQUIRY_URL = lambda: f"{settings.DATAHUB_URL}/scrap/common/mohw/MedicalLicenseInquirySimple"
_CALLBACK_URL = lambda: f"{settings.DATAHUB_URL}/scrap/captcha"
_HEADERS = lambda: {
    "Authorization": f"Token {settings.DATAHUB_TOKEN}",
    "Content-Type": "application/json",
}


def encrypt_jumin(jumin: str) -> str:
    if not settings.DATAHUB_ENC_KEY or not settings.DATAHUB_ENC_IV:
        raise ValueError("DATAHUB_ENC_KEY 또는 DATAHUB_ENC_IV가 설정되지 않았습니다.")

    key = settings.DATAHUB_ENC_KEY.encode("utf-8")
    iv = settings.DATAHUB_ENC_IV.encode("utf-8")
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted = cipher.encrypt(pad(jumin.encode("utf-8"), AES.block_size))
    return base64.b64encode(encrypted).decode("utf-8")


def _parse_license_list(data: dict) -> dict:
    license_list = data.get("LICENSELIST", [])
    for item in license_list:
        if item.get("LICENSEKIND") == "한의사":
            return {
                "verified": True,
                "license_number": item.get("LICENSENUM", ""),
                "license_date": item.get("LICENSEDATE", ""),
            }
    return {"verified": False}


async def request_verification(
    name: str,
    jumin: str,
    phone: str,
    login_option: str,
    telecom_gubun: str | None = None,
) -> dict:
    """
    Step 1: datahub에 인증 요청 전송.
    - 즉시 완료되면: {"verified": True, "license_number": ..., "license_date": ...}
    - 콜백 필요하면: {"needs_callback": True, "callback_id": ..., "callback_type": ...}
    - 실패: {"verified": False, "error": ...}
    """
    payload = {
        "LOGINOPTION": login_option,
        "JUMIN": encrypt_jumin(jumin),
        "DSNM": name,
        "PHONENUM": phone,
    }
    if telecom_gubun:
        payload["TELECOMGUBUN"] = telecom_gubun

    async with httpx.AsyncClient() as client:
        response = await client.post(
            _INQUIRY_URL(), json=payload, headers=_HEADERS(), timeout=15.0
        )
        response.raise_for_status()
        data = response.json()

    logger.warning("DATAHUB step1 raw: %s", data)

    if data.get("result") == "SUCCESS":
        return _parse_license_list(data.get("data", {}))

    # errCode 0001: 추가 인증 필요 (Naver/PASS/SMS 콜백 대기)
    if data.get("errCode") == "0001":
        cb = data.get("data", {})
        return {
            "needs_callback": True,
            "callback_id": cb.get("callbackId", ""),
            "callback_type": cb.get("callbackType", "SIMPLE"),
        }

    logger.error("DATAHUB error: %s %s", data.get("errCode"), data.get("errMsg"))
    return {"verified": False, "error": data.get("errMsg", "알 수 없는 오류")}


async def confirm_verification(
    callback_id: str,
    callback_type: str = "SIMPLE",
    callback_response: str = "",
) -> dict:
    """
    Step 2: 사용자가 앱에서 인증 완료 후 /scrap/captcha로 콜백 결과 조회.
    SIMPLE 타입(네이버 등)은 callbackResponse 불필요.
    """
    payload: dict = {
        "callbackId": callback_id,
        "callbackType": callback_type,
    }
    if callback_response:
        payload["callbackResponse"] = callback_response

    async with httpx.AsyncClient() as client:
        response = await client.post(
            _CALLBACK_URL(), json=payload, headers=_HEADERS(), timeout=30.0
        )
        response.raise_for_status()
        data = response.json()

    logger.warning("DATAHUB step2 raw: %s", data)

    if data.get("result") == "SUCCESS":
        inner = data.get("data", {})
        if isinstance(inner, dict) and inner.get("RESULT") == "FAIL":
            return {"verified": False, "error": inner.get("ERRMSG", "면허 조회 실패")}
        return _parse_license_list(inner)

    if data.get("errCode") == "0001":
        return {"needs_callback": True, "error": "아직 인증이 완료되지 않았습니다."}

    logger.error("DATAHUB confirm error: %s %s", data.get("errCode"), data.get("errMsg"))
    return {"verified": False, "error": data.get("errMsg", "알 수 없는 오류")}
