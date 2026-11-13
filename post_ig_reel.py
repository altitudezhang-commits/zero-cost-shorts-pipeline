#!/usr/bin/env python3
"""Post the next pending reel from ig_queue.json to Instagram."""
import json, subprocess, sys, os

BASE = os.path.dirname(os.path.abspath(__file__))
QPATH = os.path.join(BASE, "ig_queue.json")
ACCOUNT_ID = os.environ.get("IG_ACCOUNT_ID", "")

def main():
    if not ACCOUNT_ID:
        print("IG_ACCOUNT_ID env var is not set", file=sys.stderr)
        return 2
    with open(QPATH) as f:
        queue = json.load(f)
    nxt = next((i for i, it in enumerate(queue) if it.get("status") == "pending"), None)
    if nxt is None:
        print("QUEUE_EMPTY: no pending reels")
        return 0
    item = queue[nxt]
    video = os.path.join(BASE, item["video"])
    cover = os.path.join(BASE, item["cover"])
    cmd = ["instagram-cli", "post-feed", "--account-id", ACCOUNT_ID,
           "--file", video, "--cover", cover,
           "--video-thumbnail-playback-offset-ms", "1200",
           "--caption", item["caption"]]
    r = None
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=150)
    except subprocess.TimeoutExpired as e:
        # Fail fast: a healthy post-feed of a small file finishes well under
        # 150s. A timeout means the connector write path is hung (ghost lock
        # seen since 2026-10-12); do NOT mark posted — the caller must run the
        # duplicate check (posts, last 2 days) before concluding anything.
        out = (e.stdout or b"")[-2000:] if isinstance(e.stdout, bytes) else (e.stdout or "")[-2000:]
        err = (e.stderr or b"")[-2000:] if isinstance(e.stderr, bytes) else (e.stderr or "")[-2000:]
        print(out)
        print(err, file=sys.stderr)
        print(f"FAILED: {item['video']} rc=timeout(150s) — connector write hung, duplicate check required", file=sys.stderr)
        return 3
    print(r.stdout[-2000:])
    print(r.stderr[-2000:], file=sys.stderr)
    if r.returncode == 0:
        queue[nxt]["status"] = "posted"
        with open(QPATH, "w") as f:
            json.dump(queue, f, ensure_ascii=False, indent=2)
        print(f"POSTED: {item['video']}")
    else:
        print(f"FAILED: {item['video']} rc={r.returncode}", file=sys.stderr)
    return r.returncode

if __name__ == "__main__":
    sys.exit(main())
