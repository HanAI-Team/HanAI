"""개인정보 암호화 유틸리티.

주민등록번호 등 민감 정보를 AES-256-GCM으로 양방향 암호화한다.
EDI 생성 시 원본 복호화가 필요하므로 단방향 해시는 사용하지 않는다.

환경변수 RRN_ENCRYPTION_KEY: base64 인코딩된 32바이트 키.
키 생성: python -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"
"""

import base64
import os

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from sqlalchemy import String
from sqlalchemy.types import TypeDecorator


def _load_key() -> bytes:
    raw = os.environ.get("RRN_ENCRYPTION_KEY", "")
    if not raw:
        raise RuntimeError("환경변수 RRN_ENCRYPTION_KEY가 설정되지 않았습니다.")
    return base64.b64decode(raw)


def encrypt(plaintext: str) -> str:
    """평문 → AES-256-GCM 암호문 (base64 문자열).

    저장 형식: base64(nonce[16] + tag[16] + ciphertext)
    """
    key = _load_key()
    nonce = get_random_bytes(16)
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    ciphertext, tag = cipher.encrypt_and_digest(plaintext.encode("utf-8"))
    return base64.b64encode(nonce + tag + ciphertext).decode("ascii")


def decrypt(token: str) -> str:
    """AES-256-GCM 암호문 (base64) → 평문."""
    key = _load_key()
    data = base64.b64decode(token)
    nonce, tag, ciphertext = data[:16], data[16:32], data[32:]
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    return cipher.decrypt_and_verify(ciphertext, tag).decode("utf-8")


class EncryptedString(TypeDecorator):
    """DB 저장 시 자동 암호화, 조회 시 자동 복호화되는 SQLAlchemy 컬럼 타입."""

    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return encrypt(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return decrypt(value)
