#!/usr/bin/env python3
"""Ken Burns：manifest.json 里 status=real 的段 → 9:16 竖版 mp4（复用 trial 做法）。

用法：
  python3 kenburns.py manifest.json --durations "8.5,9.2,9.3,12.0" --out clips_dir

durations 与 manifest segments 顺序对应（seg0..segN），通常取各语种配音中最长的一段
（画面三语共用，只渲一次）。status=fallback 的段跳过（由 AI 片段补）。
"""
import json, os, subprocess, sys

FPS = 25

def motion_filter(kind, dur):
    n = max(1, int(dur * FPS))
    base = "scale=-2:2400,crop=1350:2400,format=yuv420p"
    if kind == "zoomin":
        z = f"1+0.15*on/{n}"
        zp = f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps={FPS}"
    elif kind == "zoomout":
        z = f"1.18-0.18*on/{n}"
        zp = f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps={FPS}"
    elif kind == "panright":
        zp = (f"zoompan=z='1.25':x='(iw-iw/zoom)*on/{n}':y='ih/2-(ih/zoom/2)'"
              f":d=1:s=1080x1920:fps={FPS}")
    elif kind == "panleft":
        zp = (f"zoompan=z='1.25':x='(iw-iw/zoom)*(1-on/{n})':y='ih/2-(ih/zoom/2)'"
              f":d=1:s=1080x1920:fps={FPS}")
    else:
        raise ValueError(kind)
    return base + "," + zp

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("--durations", required=True, help="逗号分隔，与 seg0..segN 对应")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    durs = [float(x) for x in a.durations.split(",")]

    with open(a.manifest, encoding="utf-8") as f:
        m = json.load(f)
    segs = sorted(m["segments"].keys())
    if len(durs) != len(segs):
        sys.exit(f"durations 数量({len(durs)})与段数({len(segs)})不一致")

    for i, seg in enumerate(segs):
        e = m["segments"][seg]
        if e.get("status") != "real":
            print(f"{seg}: fallback, skip", flush=True)
            continue
        dur = durs[i]
        vf = motion_filter(e.get("motion", "zoomin"), dur)
        outp = os.path.join(out, f"{seg}.mp4")
        cmd = ["ffmpeg", "-y", "-loop", "1", "-framerate", str(FPS),
               "-i", e["clip_path"], "-vf", vf, "-t", f"{dur:.3f}",
               "-c:v", "libx264", "-preset", "medium", "-crf", "20",
               "-pix_fmt", "yuv420p", outp]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"{seg} FAILED"); print(r.stderr[-1500:]); sys.exit(1)
        print(f"{seg} ok ({e['motion']}, {dur:.1f}s) -> {outp}", flush=True)

if __name__ == "__main__":
    main()
