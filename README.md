# TranscriptYT Python

Python packages for [TranscriptYT](https://transcript-yt.com), the YouTube Transcript API.

| Package | Install | What it is |
| --- | --- | --- |
| [`transcriptyt`](transcriptyt) | `pip install transcriptyt` | Sync and async API client |
| [`langchain-transcriptyt`](langchain-transcriptyt) | `pip install langchain-transcriptyt` | LangChain document loader and agent tools |

```python
from transcriptyt import TranscriptYT

print(TranscriptYT(api_key="ts_live_...").transcript("dQw4w9WgXcQ")["text"])
```

Get a free API key (100 credits) at [transcript-yt.com/dashboard/keys](https://transcript-yt.com/dashboard/keys). API docs: [transcript-yt.com/docs](https://transcript-yt.com/docs).

## Releasing

Bump the version, then push a tag: `transcriptyt-v0.1.1` or `langchain-transcriptyt-v0.1.1`. GitHub Actions tests, builds and publishes to PyPI with trusted publishing.
