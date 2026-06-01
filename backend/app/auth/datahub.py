import base64

import httpx
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

from app.core.config import settings


def encrypt_jumin(jumin: str) -> str:
    key = settings.DATAHUB_ENC_KEY.encode("utf-8")
    iv = settings.DATAHUB_ENC_IV.encode("utf-8")
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted = cipher.encrypt(pad(jumin.encode("utf-8"), AES.block_size))
    return base64.b64encode(encrypted).decode("utf-8")


async def verify_medical_license(
    name: str,
    jumin: str,
    phone: str,
    login_option: str,
) -> dict:
    payload = {
        "name": name,
        "jumin": encrypt_jumin(jumin),
        "phone": phone,
        "loginoption": login_option,
    }
    headers = {
        "Authorization": f"Token {settings.DATAHUB_TOKEN}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.DATAHUB_URL}/v1/mydata/medicareer",
            json=payload,
            headers=headers,
            timeout=15.0,
        )
        response.raise_for_status()
        data = response.json()

    license_list = data.get("LICENSELIST", [])
    for item in license_list:
        if item.get("LICGB") == "한의사":
            return {
                "verified": True,
                "license_number": item.get("LICNO", ""),
                "license_date": item.get("LICDATE", ""),
            }

    return {"verified": False}
