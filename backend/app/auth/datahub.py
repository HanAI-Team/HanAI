import base64
import logging

import httpx
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

from app.core.config import settings

logger = logging.getLogger(__name__)

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
