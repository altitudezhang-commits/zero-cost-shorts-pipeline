A short-video factory that costs $0 in APIs: free TTS, stock footage, Ken Burns motion and auto-assembly.

# Zero-Cost Shorts Pipeline

A small, script-based pipeline that turns a written science/trivia script into a finished vertical short video without any paid API:

1. **Fetch footage** (`fetch_footage.py`) — pull stock clips for each segment.
2. **Voice-over** (`tts_zh.py`) — synthesize narration with a free TTS endpoint (segmented synthesis, Chinese/English/Spanish voices).
3. **Motion** (`kenburns.py`) — turn still images into moving shots (pan/zoom), so the video is real motion, not a photo slideshow.
4. **Assemble** (`assemble_yt.py`, `build_science.py`) — cut segments, burn subtitles, mix background music, export H.264/yuv420p.

## Layout

- `scripts/` — one sample episode script is kept as a format example.
- `fact_sheet.md` — the fact-check sheet used for the first batch of episodes (every claim needs a source before it is narrated).
- `post_ig_reel.py` — optional posting helper. It reads the account id from the `IG_ACCOUNT_ID` environment variable and works through a local `ig_queue.json` queue file (not included; create your own).

## Notes

- Everything runs locally with ffmpeg and Python's standard tooling; the only network calls go to free public endpoints you configure yourself.
- No API keys are bundled or required by the core pipeline.

## License

MIT — see `LICENSE`.
