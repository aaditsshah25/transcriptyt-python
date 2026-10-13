# langchain-transcriptyt

[LangChain](https://www.langchain.com) integration for [TranscriptYT](https://transcript-yt.com), a YouTube Transcript API. Load YouTube transcripts into your RAG pipeline, or give an agent tools to search YouTube and read videos.

Unlike scraping YouTube directly, requests go through TranscriptYT's rotating proxies, so they keep working on cloud servers (AWS, GCP, Vercel, Colab) where YouTube blocks datacenter IPs. Supports 150+ languages, translation, and AI transcription for videos without captions.

```bash
pip install -U langchain-transcriptyt
export TRANSCRIPTYT_API_KEY="ts_live_..."   # free key: https://transcript-yt.com/dashboard/keys
```

## Document loader

```python
from langchain_transcriptyt import TranscriptYTLoader

# One Document per video
docs = TranscriptYTLoader(["https://www.youtube.com/watch?v=dQw4w9WgXcQ", "jNQXAC9IVRw"]).load()

# A whole playlist or channel (up to 50 videos), split into timestamped paragraphs
docs = TranscriptYTLoader(
    playlist="https://www.youtube.com/@3blue1brown",
    limit=20,
    chunk="paragraph",
    chunk_size=1000,
).load()
print(docs[0].metadata["source"])  # https://www.youtube.com/watch?v=...&t=42s
```

Options: `language`, `translate_to`, `chunk` (`"video"` or `"paragraph"`), `chunk_size`, `mode` (`"auto"`, `"captions"`, `"ai"`), `continue_on_failure`.

Metadata: `source`, `video_id`, `title`, `author`, `channel_id`, `language`, `translated`, `auto_generated`, `duration_seconds`, `transcript_source`, and `start`/`end` for paragraph chunks.

## Agent tools

```python
from langchain.agents import create_agent
from langchain_transcriptyt import TranscriptYTSearchTool, TranscriptYTTranscriptTool

agent = create_agent(
    "anthropic:claude-sonnet-5-5",
    tools=[TranscriptYTSearchTool(), TranscriptYTTranscriptTool()],
)
agent.invoke({"messages": [{"role": "user", "content": "Find a recent video on RAG evaluation and summarize it."}]})
```

- `youtube_transcript`: full transcript with `[HH:MM:SS]` timestamps (1 credit).
- `youtube_search`: search YouTube, optionally within a channel (free).

## Pricing

100 free credits, no card. Paid plans from $3/month. One credit per transcript; search, playlist and language lookups are free. See [transcript-yt.com/pricing](https://transcript-yt.com/pricing).

## License

MIT
