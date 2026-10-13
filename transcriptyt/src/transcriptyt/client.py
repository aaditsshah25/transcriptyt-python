from __future__ import annotations

import asyncio
import os
import time
from typing import Any, Literal, Optional, Sequence, Union

import httpx

from ._version import __version__

DEFAULT_BASE_URL = "https://transcript-yt.com"
DEFAULT_TIMEOUT = 300.0
RETRY_STATUSES = {429, 502, 503, 504}

Format = Literal["json", "text", "srt", "vtt", "csv", "md"]
CaptionType = Literal["any", "manual", "auto"]
Mode = Literal["auto", "captions", "ai"]


class TranscriptYTError(Exception):
    """Raised for any non-2xx response. `code` is the API error code, e.g. NO_CAPTIONS."""

    def __init__(self, message: str, *, code: str, status: int, body: Any = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status
        self.body = body

    def __repr__(self) -> str:
        return f"TranscriptYTError(code={self.code!r}, status={self.status}, message={self.message!r})"


def _error_from(response: httpx.Response) -> TranscriptYTError:
    try:
        body = response.json()
    except ValueError:
        return TranscriptYTError(response.text or response.reason_phrase, code="HTTP_ERROR", status=response.status_code)
    error = body.get("error") if isinstance(body, dict) else None
    if isinstance(error, dict):
        return TranscriptYTError(error.get("message", ""), code=error.get("code", "HTTP_ERROR"), status=response.status_code, body=body)
    if response.status_code == 402 or error == "Out of credits":
        return TranscriptYTError("Out of credits.", code="OUT_OF_CREDITS", status=response.status_code, body=body)
    return TranscriptYTError(str(error or body), code="HTTP_ERROR", status=response.status_code, body=body)


def _retry_delay(response: httpx.Response, attempt: int) -> float:
    retry_after = response.headers.get("retry-after")
    if retry_after and retry_after.isdigit():
        return min(float(retry_after), 30.0)
    reset = response.headers.get("x-ratelimit-reset")
    if reset and reset.isdigit():
        return min(max(int(reset) - time.time(), 1.0), 30.0)
    return min(2.0**attempt, 30.0)


def _clean(params: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in params.items() if v is not None}


def _transcript_body(
    url: str,
    language: Optional[str],
    translate_to: Optional[str],
    format: Format,
    include_segments: bool,
    timestamps: bool,
    paragraphs: bool,
    chunk_size: Optional[int],
    caption_type: CaptionType,
    original_language: bool,
    mode: Mode,
    start_time: Optional[float],
    end_time: Optional[float],
    search: Optional[str],
) -> dict[str, Any]:
    return _clean(
        {
            "url": url,
            "language": language,
            "translate_to": translate_to,
            "format": format,
            "includeSegments": include_segments,
            "timestamps": timestamps,
            "paragraphs": paragraphs,
            "chunkSize": chunk_size,
            "captionType": caption_type,
            "originalLanguage": original_language,
            "mode": mode,
            "startTime": start_time,
            "endTime": end_time,
            "search": search,
        }
    )


class _Base:
    def __init__(self, api_key: Optional[str], base_url: Optional[str]):
        api_key = api_key or os.environ.get("TRANSCRIPTYT_API_KEY")
        if not api_key:
            raise ValueError(
                "Missing API key. Pass api_key=... or set TRANSCRIPTYT_API_KEY. "
                "Get a free key at https://transcript-yt.com/dashboard/keys"
            )
        self.base_url = (base_url or os.environ.get("TRANSCRIPTYT_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "User-Agent": f"transcriptyt-python/{__version__}",
        }

    @staticmethod
    def _parse(response: httpx.Response) -> Any:
        if response.headers.get("content-type", "").startswith("application/json"):
            return response.json()
        return response.text


class TranscriptYT(_Base):
    """Client for the TranscriptYT YouTube Transcript API.

    >>> from transcriptyt import TranscriptYT
    >>> client = TranscriptYT()  # reads TRANSCRIPTYT_API_KEY
    >>> client.transcript("https://www.youtube.com/watch?v=dQw4w9WgXcQ")["text"]
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = 2,
        http_client: Optional[httpx.Client] = None,
    ):
        super().__init__(api_key, base_url)
        self.max_retries = max_retries
        self._client = http_client or httpx.Client(timeout=timeout)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "TranscriptYT":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def _request(self, method: str, path: str, *, params: Optional[dict] = None, json: Optional[dict] = None) -> Any:
        for attempt in range(self.max_retries + 1):
            response = self._client.request(
                method, self.base_url + path, params=_clean(params or {}), json=json, headers=self._headers
            )
            if response.status_code in RETRY_STATUSES and attempt < self.max_retries:
                time.sleep(_retry_delay(response, attempt))
                continue
            if response.is_error:
                raise _error_from(response)
            return self._parse(response)

    def transcript(
        self,
        url: str,
        *,
        language: Optional[str] = None,
        translate_to: Optional[str] = None,
        format: Format = "json",
        include_segments: bool = True,
        timestamps: bool = False,
        paragraphs: bool = False,
        chunk_size: Optional[int] = None,
        caption_type: CaptionType = "any",
        original_language: bool = False,
        mode: Mode = "auto",
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        search: Optional[str] = None,
    ) -> Union[dict, str]:
        """Fetch one video's transcript. Returns a dict for format="json", otherwise the formatted string."""
        body = _transcript_body(
            url, language, translate_to, format, include_segments, timestamps, paragraphs, chunk_size,
            caption_type, original_language, mode, start_time, end_time, search,
        )
        return self._request("POST", "/v1/transcript", json=body)

    def transcripts(
        self,
        urls: Optional[Sequence[str]] = None,
        *,
        playlist: Optional[str] = None,
        limit: Optional[int] = None,
        **options: Any,
    ) -> dict:
        """Fetch up to 50 transcripts in one call, from `urls` or a playlist/channel URL.

        Extra keyword arguments are passed through as transcript options (e.g. language="en", format="text").
        A failed video does not fail the batch; check each result's `ok`.
        """
        if not urls and not playlist:
            raise ValueError("Provide urls or playlist.")
        body = _clean({"urls": list(urls) if urls else None, "playlist": playlist, "limit": limit, **options})
        return self._request("POST", "/v1/transcripts", json=body)

    def languages(self, url: str) -> dict:
        """List the caption tracks a video has. Free."""
        return self._request("GET", "/v1/languages", params={"url": url})

    def playlist(self, url: str, *, limit: Optional[int] = None) -> dict:
        """List the videos in a playlist or a channel's uploads. Free."""
        return self._request("GET", "/v1/playlist", params={"url": url, "limit": limit})

    def search(self, q: str, *, channel: Optional[str] = None, limit: Optional[int] = None) -> dict:
        """Search YouTube videos, optionally within one channel. Free."""
        return self._request("GET", "/v1/search", params={"q": q, "channel": channel, "limit": limit})

    def summary(self, url: str, *, language: Optional[str] = None, translate_to: Optional[str] = None) -> dict:
        """AI summary, key points, and timestamped notes for a video."""
        return self._request("POST", "/v1/summary", json=_clean({"url": url, "language": language, "translate_to": translate_to}))

    def usage(self) -> dict:
        """Plan, credits used and remaining."""
        return self._request("GET", "/v1/usage")


class AsyncTranscriptYT(_Base):
    """Async client with the same methods as `TranscriptYT`."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = 2,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        super().__init__(api_key, base_url)
        self.max_retries = max_retries
        self._client = http_client or httpx.AsyncClient(timeout=timeout)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "AsyncTranscriptYT":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.aclose()

    async def _request(self, method: str, path: str, *, params: Optional[dict] = None, json: Optional[dict] = None) -> Any:
        for attempt in range(self.max_retries + 1):
            response = await self._client.request(
                method, self.base_url + path, params=_clean(params or {}), json=json, headers=self._headers
            )
            if response.status_code in RETRY_STATUSES and attempt < self.max_retries:
                await asyncio.sleep(_retry_delay(response, attempt))
                continue
            if response.is_error:
                raise _error_from(response)
            return self._parse(response)

    async def transcript(
        self,
        url: str,
        *,
        language: Optional[str] = None,
        translate_to: Optional[str] = None,
        format: Format = "json",
        include_segments: bool = True,
        timestamps: bool = False,
        paragraphs: bool = False,
        chunk_size: Optional[int] = None,
        caption_type: CaptionType = "any",
        original_language: bool = False,
        mode: Mode = "auto",
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        search: Optional[str] = None,
    ) -> Union[dict, str]:
        body = _transcript_body(
            url, language, translate_to, format, include_segments, timestamps, paragraphs, chunk_size,
            caption_type, original_language, mode, start_time, end_time, search,
        )
        return await self._request("POST", "/v1/transcript", json=body)

    async def transcripts(
        self,
        urls: Optional[Sequence[str]] = None,
        *,
        playlist: Optional[str] = None,
        limit: Optional[int] = None,
        **options: Any,
    ) -> dict:
        if not urls and not playlist:
            raise ValueError("Provide urls or playlist.")
        body = _clean({"urls": list(urls) if urls else None, "playlist": playlist, "limit": limit, **options})
        return await self._request("POST", "/v1/transcripts", json=body)

    async def languages(self, url: str) -> dict:
        return await self._request("GET", "/v1/languages", params={"url": url})

    async def playlist(self, url: str, *, limit: Optional[int] = None) -> dict:
        return await self._request("GET", "/v1/playlist", params={"url": url, "limit": limit})

    async def search(self, q: str, *, channel: Optional[str] = None, limit: Optional[int] = None) -> dict:
        return await self._request("GET", "/v1/search", params={"q": q, "channel": channel, "limit": limit})

    async def summary(self, url: str, *, language: Optional[str] = None, translate_to: Optional[str] = None) -> dict:
        return await self._request("POST", "/v1/summary", json=_clean({"url": url, "language": language, "translate_to": translate_to}))

    async def usage(self) -> dict:
        return await self._request("GET", "/v1/usage")
