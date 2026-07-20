import asyncio
import json

import httpx
import pytest

from app.charting.stt import client as client_module
from app.charting.stt.client import VitoSpeechClient, load_vito_keywords

_real_sleep = asyncio.sleep  # 폴링 대기(RTZR_POLL_INTERVAL_SEC=5초)를 테스트에서 건너뛰기 위한 원본 참조


def _client():
    client = VitoSpeechClient()
    client.client_id = "test-client-id"
    client.client_secret = "test-client-secret"
    client._keywords = []  # 실제 glossary.json 로딩과 분리해 결정론적으로 테스트
    return client


def test_발화_기반_화자분리_텍스트_생성():
    result = _client()._parse_segments({
        "results": {"utterances": [
            {"spk": 1, "msg": "안녕하세요"},
            {"spk": 2, "msg": "네, 말씀하세요"},
        ]}
    })
    assert result == "[화자1] 안녕하세요\n[화자2] 네, 말씀하세요"


def test_빈_텍스트_발화는_제외됨():
    result = _client()._parse_segments({
        "results": {"utterances": [
            {"spk": 1, "msg": "안녕하세요"},
            {"spk": 2, "msg": "   "},
        ]}
    })
    assert result == "[화자1] 안녕하세요"


def test_utterances_없으면_빈_문자열_반환():
    result = _client()._parse_segments({"results": {"utterances": []}})
    assert result == ""


def test_화자_번호가_0이면_정상_처리됨():
    result = _client()._parse_segments({
        "results": {"utterances": [{"spk": 0, "msg": "안녕하세요"}]}
    })
    assert result == "[화자0] 안녕하세요"


async def test_빈_오디오는_빈_문자열_반환():
    assert await _client().transcribe(b"") == ""


async def test_인증정보_없으면_예외_발생():
    client = VitoSpeechClient()
    client.client_id = None
    client.client_secret = None
    with pytest.raises(ValueError):
        await client.transcribe(b"audio-bytes")


def test_키워드_500개_제한이_지켜짐(tmp_path, monkeypatch):
    glossary = {
        "priority": [f"우선{i}" for i in range(10)],
        "auto": [f"자동{i}" for i in range(20)],
    }
    path = tmp_path / "glossary.json"
    path.write_text(json.dumps(glossary, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(client_module, "GLOSSARY_PATH", str(path))

    result = load_vito_keywords(limit=15)
    assert len(result) == 15
    assert all(w.startswith("우선") for w in result[:10])  # priority 전부 포함


def test_glossary_없으면_빈_키워드_반환(tmp_path, monkeypatch):
    monkeypatch.setattr(client_module, "GLOSSARY_PATH", str(tmp_path / "missing.json"))
    assert load_vito_keywords() == []


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
    """auth(POST) -> submit(POST) -> poll(GET) 3단계 흐름을 URL로 라우팅하는 fake."""

    def __init__(self, auth_response=None, submit_response=None, poll_responses=None,
                 submit_exc=None, auth_exc=None):
        self._auth_response = auth_response
        self._submit_response = submit_response
        self._poll_responses = list(poll_responses or [])
        self._submit_exc = submit_exc
        self._auth_exc = auth_exc

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def post(self, url, **kwargs):
        if url == client_module.RTZR_AUTH_URL:
            if self._auth_exc:
                raise self._auth_exc
            return self._auth_response
        if url == client_module.RTZR_TRANSCRIBE_URL:
            if self._submit_exc:
                raise self._submit_exc
            return self._submit_response
        raise AssertionError(f"예상치 못한 POST 호출: {url}")

    async def get(self, url, **kwargs):
        return self._poll_responses.pop(0)


async def test_정상_응답시_화자분리_텍스트_반환(monkeypatch):
    monkeypatch.setattr(asyncio, "sleep", lambda *a, **k: _real_sleep(0))
    auth = _FakeResponse({"access_token": "tok"})
    submit = _FakeResponse({"id": "job-1"})
    poll = _FakeResponse({"status": "completed", "results": {"utterances": [
        {"spk": 1, "msg": "안녕하세요"},
    ]}})
    monkeypatch.setattr(
        httpx, "AsyncClient",
        lambda **kwargs: _FakeAsyncClient(auth_response=auth, submit_response=submit, poll_responses=[poll]),
    )

    result = await _client().transcribe(b"audio-bytes")
    assert result == "[화자1] 안녕하세요"


async def test_completed_되기_전까지_폴링을_반복함(monkeypatch):
    monkeypatch.setattr(asyncio, "sleep", lambda *a, **k: _real_sleep(0))
    auth = _FakeResponse({"access_token": "tok"})
    submit = _FakeResponse({"id": "job-1"})
    polls = [
        _FakeResponse({"status": "processing"}),
        _FakeResponse({"status": "processing"}),
        _FakeResponse({"status": "completed", "results": {"utterances": [{"spk": 1, "msg": "완료"}]}}),
    ]
    monkeypatch.setattr(
        httpx, "AsyncClient",
        lambda **kwargs: _FakeAsyncClient(auth_response=auth, submit_response=submit, poll_responses=polls),
    )

    result = await _client().transcribe(b"audio-bytes")
    assert result == "[화자1] 완료"


async def test_전사_실패_상태면_예외_발생(monkeypatch):
    monkeypatch.setattr(asyncio, "sleep", lambda *a, **k: _real_sleep(0))
    auth = _FakeResponse({"access_token": "tok"})
    submit = _FakeResponse({"id": "job-1"})
    poll = _FakeResponse({"status": "failed"})
    monkeypatch.setattr(
        httpx, "AsyncClient",
        lambda **kwargs: _FakeAsyncClient(auth_response=auth, submit_response=submit, poll_responses=[poll]),
    )

    with pytest.raises(RuntimeError):
        await _client().transcribe(b"audio-bytes")


async def test_API_오류_응답시_예외_전파(monkeypatch):
    auth = _FakeResponse({"access_token": "tok"})
    submit = _FakeResponse({"error": "bad request"}, status_code=400)
    monkeypatch.setattr(
        httpx, "AsyncClient",
        lambda **kwargs: _FakeAsyncClient(auth_response=auth, submit_response=submit),
    )

    with pytest.raises(httpx.HTTPStatusError):
        await _client().transcribe(b"audio-bytes")


async def test_키워드에_공백있고_400이면_공백제거후_재시도(monkeypatch):
    monkeypatch.setattr(asyncio, "sleep", lambda *a, **k: _real_sleep(0))
    auth = _FakeResponse({"access_token": "tok"})
    bad_submit = _FakeResponse({"error": "invalid keywords"}, status_code=400)
    good_submit = _FakeResponse({"id": "job-1"})
    poll = _FakeResponse({"status": "completed", "results": {"utterances": [{"spk": 1, "msg": "재시도 성공"}]}})

    call_count = {"n": 0}

    class _RetryFakeClient(_FakeAsyncClient):
        async def post(self, url, **kwargs):
            if url == client_module.RTZR_TRANSCRIBE_URL:
                call_count["n"] += 1
                return bad_submit if call_count["n"] == 1 else good_submit
            return await super().post(url, **kwargs)

    monkeypatch.setattr(
        httpx, "AsyncClient",
        lambda **kwargs: _RetryFakeClient(auth_response=auth, poll_responses=[poll]),
    )

    test_client = _client()
    test_client._keywords = ["감기 몸살"]  # 공백 포함 키워드 — 재시도 유도
    result = await test_client.transcribe(b"audio-bytes")
    assert result == "[화자1] 재시도 성공"
    assert call_count["n"] == 2


async def test_타임아웃시_예외_전파(monkeypatch):
    monkeypatch.setattr(
        httpx, "AsyncClient",
        lambda **kwargs: _FakeAsyncClient(auth_exc=httpx.TimeoutException("timeout")),
    )

    with pytest.raises(httpx.TimeoutException):
        await _client().transcribe(b"audio-bytes")
