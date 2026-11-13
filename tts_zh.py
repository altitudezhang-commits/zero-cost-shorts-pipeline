#!/usr/bin/env python3
"""中文配音：Google Translate TTS 分段合成（系统 tts CLI 授权失效时的备用方案）。
用法: python3 tts_zh.py [--tl zh-CN] out.mp3 < segments.txt  (每行一段)
"""
import argparse, subprocess, sys, urllib.parse, os

def synth(text, out, tl):
    url = ("https://translate.google.com/translate_tts?ie=UTF-8&tl=" + tl
           + "&client=tw-ob&q=" + urllib.parse.quote(text))
    r = subprocess.run(["curl", "-sL", "-A", "Mozilla/5.0", "-o", out, url],
                       capture_output=True, text=True, timeout=60)
    if r.returncode != 0 or os.path.getsize(out) < 1000:
        raise RuntimeError(f"TTS failed for segment: {text[:20]}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tl", default="zh-CN", help="TTS voice language, e.g. zh-CN, en, es")
    ap.add_argument("out")
    a = ap.parse_args()
    out = a.out
    segs = [l.strip() for l in sys.stdin.read().splitlines() if l.strip()]
    assert segs, "no segments"
    tmp = []
    for i, s in enumerate(segs):
        p = f"/tmp/tts_seg{i}.mp3"
        synth(s, p, a.tl)
        tmp.append(p)
        print(f"seg {i} ok ({len(s)} chars)", flush=True)
    # concat
    cmd = ["ffmpeg", "-y"]
    for p in tmp: cmd += ["-i", p]
    filt = "".join(f"[{i}:a]" for i in range(len(tmp))) + f"concat=n={len(tmp)}:v=0:a=1"
    cmd += ["-filter_complex", filt, "-c:a", "libmp3lame", "-b:a", "128k", out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("concat failed: " + r.stderr[-500:])
    for p in tmp: os.remove(p)
    print("saved", out, f"{os.path.getsize(out)/1e6:.1f}MB", flush=True)

if __name__ == "__main__":
    main()
