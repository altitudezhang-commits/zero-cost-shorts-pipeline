#!/usr/bin/env python3
"""竖版科普视频合成：4片段 -> 1080x1920 -> 配音 -> 字幕（可选烧录）。
用法: python3 assemble_yt.py spec.json
spec.json: {"clips": [...4个mp4路径...], "vo": "vo.mp3", "subs": [...4段字幕...],
            "out": "finished_xxx.mp4"}
可选字段（2026-10-23 改版：画面不再烧录字幕，改走 CC 软字幕）：
  "burn": false        -> 不把字幕烧进画面（默认 true，老行为）
  "srt_out": "path"    -> 把主字幕 .srt 写到该路径留档（供上传 CC 字幕轨）
  "extra_subs": {"zh-CN": [...4段...], "es": [...4段...]}
                       -> 额外语言字幕 .srt 写到 srt_out 同目录、
                          文件名 <stem>_<lang>.srt（时间轴与主字幕相同）
字幕段内换行用 \\N。
"""
import json, os, subprocess, sys

FONTSDIR = "/usr/share/fonts/opentype/noto"
STYLE = ("FontName=Noto Sans CJK SC,FontSize=24,PrimaryColour=&H00FFFFFF,"
         "OutlineColour=&H80000000,BorderStyle=1,Outline=2,Shadow=0,"
         "MarginV=90,Alignment=2")

def probe_dur(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", path], capture_output=True, text=True)
    return float(r.stdout.strip())

def srt_time(s):
    h, m = divmod(int(s), 3600); m, sec = divmod(m, 60)
    ms = int(round((s - int(s)) * 1000))
    return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"

def main():
    spec = json.load(open(sys.argv[1]))
    clips, vo, subs, out = spec["clips"], spec["vo"], spec["subs"], spec["out"]
    assert len(clips) == 4 and len(subs) == 4, "need 4 clips + 4 subtitle segs"
    for c in clips: assert os.path.exists(c), f"missing clip {c}"
    assert os.path.exists(vo), f"missing vo {vo}"
    durs = [probe_dur(c) for c in clips]
    vo_dur = probe_dur(vo)
    cum = [0.0]
    for d in durs: cum.append(cum[-1] + d)
    bounds = [(cum[i], cum[i+1] if i < 3 else min(cum[i+1], vo_dur)) for i in range(4)]
    def write_srt(path, lines):
        with open(path, "w", encoding="utf-8") as f:
            for i, ((s, e), t) in enumerate(zip(bounds, lines), 1):
                f.write(f"{i}\n{srt_time(s)} --> {srt_time(e)}\n{t}\n\n")
    srt = "/tmp/subs_yt.srt"
    write_srt(srt, subs)
    burn = spec.get("burn", True)
    srt_out = spec.get("srt_out")
    if srt_out:
        write_srt(srt_out, subs)
        stem, _ = os.path.splitext(srt_out)
        for lang, lines in (spec.get("extra_subs") or {}).items():
            assert len(lines) == 4, f"extra_subs[{lang}] need 4 segs"
            write_srt(f"{stem}_{lang}.srt", lines)
    scales = "".join(f"[{i}:v]scale=1080:1920,setsar=1[v{i}];" for i in range(4))
    if burn:
        fc = (scales + "[v0][v1][v2][v3]concat=n=4:v=1:a=0,"
              f"subtitles={srt}:fontsdir={FONTSDIR}:force_style='{STYLE}'[v]")
    else:
        fc = scales + "[v0][v1][v2][v3]concat=n=4:v=1:a=0[v]"
    cmd = ["ffmpeg", "-y"]
    for c in clips: cmd += ["-i", c]
    cmd += ["-i", vo, "-filter_complex", fc, "-map", "[v]", "-map", "4:a",
            "-c:a", "aac", "-b:a", "128k", "-shortest",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", out]
    print("building", out, "clips:", [f"{d:.1f}s" for d in durs], flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=1200)
    if r.returncode != 0:
        print("FAILED"); print(r.stderr[-2000:]); sys.exit(1)
    print("OK", out, f"{os.path.getsize(out)/1e6:.1f}MB", f"dur={probe_dur(out):.1f}s")

if __name__ == "__main__":
    main()
