import httpx
import pytest
import respx

from transcriptyt import TranscriptYT, TranscriptYTError

BASE = "https://transcript-yt.com"


@respx.mock
def test_transcript_sends_auth_and_body():
    route = respx.post(f"{BASE}/v1/transcript").mock(
        return_value=httpx.Response(200, json={"videoId": "abc", "text": "hi", "segments": []})
    )
    client = TranscriptYT(api_key="ts_live_x")
    assert client.transcript("abc", translate_to="es")["text"] == "hi"
    request = route.calls.last.request
    assert request.headers["authorization"] == "Bearer ts_live_x"
    assert b'"translate_to":"es"' in request.content.replace(b" ", b"")


@respx.mock
def test_text_format_returns_string():
    respx.post(f"{BASE}/v1/transcript").mock(
        return_value=httpx.Response(200, text="hello", headers={"content-type": "text/plain"})
    )
    assert TranscriptYT(api_key="k").transcript("abc", format="text") == "hello"


@respx.mock
def test_error_raises_with_code():
    respx.post(f"{BASE}/v1/transcript").mock(
        return_value=httpx.Response(404, json={"error": {"code": "NO_CAPTIONS", "message": "none"}})
    )
    with pytest.raises(TranscriptYTError) as e:
        TranscriptYT(api_key="k").transcript("abc")
    assert e.value.code == "NO_CAPTIONS" and e.value.status == 404


@respx.mock
def test_retries_on_429():
    route = respx.get(f"{BASE}/v1/usage").mock(
        side_effect=[httpx.Response(429, headers={"retry-after": "0"}, json={"error": {"code": "RATE_LIMITED", "message": ""}}),
                     httpx.Response(200, json={"plan": "FREE"})]
    )
    assert TranscriptYT(api_key="k").usage() == {"plan": "FREE"}
    assert route.call_count == 2


def test_missing_key(monkeypatch):
    monkeypatch.delenv("TRANSCRIPTYT_API_KEY", raising=False)
    with pytest.raises(ValueError):
        TranscriptYT()
