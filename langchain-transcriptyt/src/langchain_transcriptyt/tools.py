from __future__ import annotations

from typing import Optional, Type

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from pydantic import BaseModel, ConfigDict, Field
from transcriptyt import TranscriptYT, TranscriptYTError


class TranscriptInput(BaseModel):
    url: str = Field(description="YouTube video URL or 11-character video ID.")
    language: Optional[str] = Field(default=None, description="BCP-47 code of the caption track, e.g. 'en'.")
    translate_to: Optional[str] = Field(default=None, description="Translate the transcript into this BCP-47 language.")


class SearchInput(BaseModel):
    query: str = Field(description="What to search YouTube for.")
    channel: Optional[str] = Field(default=None, description="Restrict to this channel URL or @handle.")
    limit: int = Field(default=10, description="Max videos to return (1-50).")


class TranscriptYTTranscriptTool(BaseTool):
    """Fetch a YouTube video's transcript as plain text with timestamps.

    Setup:
        .. code-block:: bash

            pip install -U langchain-transcriptyt
            export TRANSCRIPTYT_API_KEY="ts_live_..."

    Invoke:
        .. code-block:: python

            from langchain_transcriptyt import TranscriptYTTranscriptTool

            tool = TranscriptYTTranscriptTool()
            tool.invoke({"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"})
    """

    name: str = "youtube_transcript"
    description: str = (
        "Get the full transcript of a YouTube video, with [HH:MM:SS] timestamps. "
        "Input is a YouTube URL or video ID. Use it to answer questions about, summarize, or quote a video."
    )
    args_schema: Type[BaseModel] = TranscriptInput
    client: TranscriptYT = Field(default_factory=TranscriptYT)
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def _run(
        self,
        url: str,
        language: Optional[str] = None,
        translate_to: Optional[str] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        try:
            return self.client.transcript(
                url, language=language, translate_to=translate_to, format="md", timestamps=True, paragraphs=True
            )
        except TranscriptYTError as e:
            return f"Error {e.code}: {e.message}"


class TranscriptYTSearchTool(BaseTool):
    """Search YouTube videos and return titles, channels and URLs.

    Invoke:
        .. code-block:: python

            from langchain_transcriptyt import TranscriptYTSearchTool

            TranscriptYTSearchTool().invoke({"query": "langchain tutorial", "limit": 5})
    """

    name: str = "youtube_search"
    description: str = (
        "Search YouTube for videos. Returns one line per video: title, channel, duration and URL. "
        "Pair with youtube_transcript to read a result."
    )
    args_schema: Type[BaseModel] = SearchInput
    client: TranscriptYT = Field(default_factory=TranscriptYT)
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def _run(
        self,
        query: str,
        channel: Optional[str] = None,
        limit: int = 10,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        try:
            result = self.client.search(query, channel=channel, limit=limit)
        except TranscriptYTError as e:
            return f"Error {e.code}: {e.message}"
        lines = []
        for v in result.get("videos", []):
            minutes = f"{v['durationSeconds'] // 60}:{v['durationSeconds'] % 60:02d}" if v.get("durationSeconds") else None
            parts = [v.get("title"), v.get("channelTitle"), minutes, v.get("published")]
            lines.append(" | ".join(str(p) for p in parts if p) + f" | https://www.youtube.com/watch?v={v['videoId']}")
        return "\n".join(lines) or "No videos found."
