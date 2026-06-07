import json

import httpx
import pytest

from app.charting.stt.client import ClovaSpeechClient


def _client():
    client = ClovaSpeechClient()
    client.secret_key = "test-key"
    client.invoke_url = "http://test-invoke-url"
    return client


def test_세그먼트_기반_화자분리_텍스트_생성():
    result = _client()._parse_segments({
        "segments": [
            {"speaker": {"name": "A"}, "text": "안녕하세요"},
            {"speaker": {"name": "B"}, "text": "네, 말씀하세요"},
        ]
    })
    assert result == "[A] 안녕하세요\n[B] 네, 말씀하세요"


def test_빈_텍스트_세그먼트는_제외됨():
    result = _client()._parse_segments({
        "segments": [
            {"speaker": {"name": "A"}, "text": "안녕하세요"},
            {"speaker": {"name": "B"}, "text": "   "},
        ]
    })
    assert result == "[A] 안녕하세요"


def test_segments_없으면_전체_텍스트_반환():
    result = _client()._parse_segments({"text": "전체 텍스트입니다"})
    assert result == "전체 텍스트입니다"


def test_화자_이름_없으면_기본값_사용():
    result = _client()._parse_segments({
        "segments": [{"speaker": {}, "text": "안녕하세요"}]
    })
    assert result == "[화자] 안녕하세요"


async def test_빈_오디오는_빈_문자열_반환():
    assert await _client().transcribe(b"") == ""


async def test_인증정보_없으면_예외_발생():
    client = ClovaSpeechClient()
    client.secret_key = None
    client.invoke_url = None
    with pytest.raises(ValueError):
        await client.transcribe(b"audio-bytes")


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = json.dumps(payload)

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("POST", "http://test")
            raise httpx.HTTPStatusError(
                "error",
                request=request,
                response=httpx.Response(self.status_code, request=request, text=self.text),
            )

    def json(self):
        return self._payload


class _FakeAsyncClient:
    def __init__(self, response=None, exc=None):
        self._response = response
        self._exc = exc

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def post(self, url, **kwargs):
        if self._exc:
            raise self._exc
        return self._response


async def test_정상_응답시_화자분리_텍스트_반환(monkeypatch):
    response = _FakeResponse({"segments": [{"speaker": {"name": "A"}, "text": "안녕하세요"}]})
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: _FakeAsyncClient(response=response))

    result = await _client().transcribe(b"audio-bytes")
    assert result == "[A] 안녕하세요"


async def test_API_오류_응답시_예외_전파(monkeypatch):
    response = _FakeResponse({"error": "bad request"}, status_code=400)
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: _FakeAsyncClient(response=response))

    with pytest.raises(httpx.HTTPStatusError):
        await _client().transcribe(b"audio-bytes")


async def test_타임아웃시_예외_전파(monkeypatch):
    monkeypatch.setattr(
        httpx, "AsyncClient", lambda **kwargs: _FakeAsyncClient(exc=httpx.TimeoutException("timeout"))
    )

    with pytest.raises(httpx.TimeoutException):
        await _client().transcribe(b"audio-bytes")
