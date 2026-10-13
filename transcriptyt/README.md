# transcriptyt

Python client for the [TranscriptYT](https://transcript-yt.com) YouTube Transcript API. Get any public video's transcript as JSON, text, SRT, VTT, CSV or Markdown, in 150+ languages, with AI transcription when a video has no captions. Requests run through rotating proxies, so they keep working from cloud servers where YouTube blocks direct scraping.

```bash
pip install transcriptyt
```

Get a free API key (100 credits) at [transcript-yt.com/dashboard/keys](https://transcript-yt.com/dashboard/keys).

## Usage

```python
from transcriptyt import TranscriptYT

client = TranscriptYT()  # reads TRANSCRIPTYT_API_KEY, or pass api_key="ts_live_..."

t = client.transcript("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
print(t["title"], t["language"])
print(t["text"])
for seg in t["segments"][:3]:
    print(seg["timestamp"], seg["text"])

# Other formats return a string
srt = client.transcript("dQw4w9WgXcQ", format="srt")

# Translate, or pick a language
client.transcript("dQw4w9WgXcQ", translate_to="es")
client.transcript("dQw4w9WgXcQ", language="de")

# Up to 50 videos per call, or a whole playlist/channel
batch = client.transcripts(["dQw4w9WgXcQ", "jNQXAC9IVRw"], format="text")
batch = client.transcripts(playlist="https://www.youtube.com/@mkbhd", limit=20)
for r in batch["results"]:
    print(r["url"], r["ok"])

# Free endpoints
client.search("python tutorial", limit=10)
client.playlist("https://www.youtube.com/playlist?list=...")
client.languages("dQw4w9WgXcQ")
client.usage()

# AI summary, key points and timestamped notes
client.summary("dQw4w9WgXcQ")
```

### Async

```python
from transcriptyt import AsyncTranscriptYT

async with AsyncTranscriptYT() as client:
    t = await client.transcript("dQw4w9WgXcQ")
```

### Errors

Every non-2xx response raises `TranscriptYTError` with `.code` (e.g. `NO_CAPTIONS`, `VIDEO_UNAVAILABLE`, `RATE_LIMITED`, `OUT_OF_CREDITS`), `.status` and `.message`. Rate-limit and capacity responses (429/503) are retried automatically (`max_retries=2`).

```python
from transcriptyt import TranscriptYTError

try:
    client.transcript("dQw4w9WgXcQ", mode="captions")
except TranscriptYTError as e:
    print(e.code, e.message)
```

## Transcript options

| Argument | Description |
| --- | --- |
| `language` | BCP-47 code of the track to fetch |
| `translate_to` | Machine-translate to this language (150+), keeping timing |
| `format` | `json` (default), `text`, `srt`, `vtt`, `csv`, `md` |
| `include_segments` | `False` returns only the full text (JSON) |
| `timestamps` | Prefix lines with `[HH:MM:SS]` in text/md |
| `paragraphs`, `chunk_size` | Merge segments into paragraphs of up to `chunk_size` characters |
| `caption_type` | `any`, `manual`, `auto` |
| `original_language` | Prefer the spoken language over English |
| `mode` | `auto` (captions, then AI), `captions` (never AI), `ai` |
| `start_time`, `end_time` | Only part of the video, in seconds |
| `search` | Only lines containing this text |

Full API reference: [transcript-yt.com/docs](https://transcript-yt.com/docs). Using LangChain? See [`langchain-transcriptyt`](https://pypi.org/project/langchain-transcriptyt/).

## License

MIT
