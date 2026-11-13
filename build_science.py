#!/usr/bin/env python3
"""science_v1 B阶段合成：4片段拼接→1080x1920→配音→烧录字幕"""
import os, subprocess, glob, json

BASE = os.path.expanduser("~/workspace/media/science_v1")
CLIPS = os.path.join(BASE, "clips")
FONTSDIR = "/usr/share/fonts/opentype/noto"
STYLE = ("FontName=Noto Sans CJK SC,FontSize=24,PrimaryColour=&H00FFFFFF,"
         "OutlineColour=&H80000000,BorderStyle=1,Outline=2,Shadow=0,"
         "MarginV=90,Alignment=2")

def clip_paths(prefix):
    files = sorted(glob.glob(os.path.join(CLIPS, f"media-generation-{prefix}-?.mp4")) +
                   glob.glob(os.path.join(CLIPS, f"media-generation-{prefix}-?-0-*.mp4")))
    # 按 _1.._4 排序去重
    seen, out = set(), []
    for f in sorted(files):
        key = f.split(f"{prefix}-")[1][0]
        if key not in seen:
            seen.add(key); out.append(f)
    return out

def probe_dur(path):
    r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
                        "-of","csv=p=0",path], capture_output=True, text=True)
    return float(r.stdout.strip())

def srt_time(s):
    h, m = divmod(int(s), 3600); m, sec = divmod(m, 60)
    ms = int(round((s - int(s)) * 1000))
    return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"

def write_srt(path, segments):
    with open(path, "w", encoding="utf-8") as f:
        for i, (start, end, text) in enumerate(segments, 1):
            f.write(f"{i}\n{srt_time(start)} --> {srt_time(end)}\n{text}\n\n")

VIDEOS = [
    dict(name="finished_冷知识1_章鱼_竖版.mp4", prefix="zhangyu",
         vo="vo_zhangyu.mp3",
         subs=["你知道吗？章鱼有三颗心脏，流的血还是蓝色的！",
               "其中两颗叫鳃心，专门给鳃供血，另一颗主心脏管全身。",
               "它的血液靠含铜的血蓝蛋白运氧，所以血是蓝的；\\N蓝血特别黏稠，循环很费劲，这就是需要三颗心的原因。",
               "章鱼一游泳主心脏就停工，游一会儿就累，\\N所以它宁愿在海底爬。你还知道哪些离谱的深海生物？评论区聊聊！"]),
    dict(name="finished_冷知识2_香蕉草莓_竖版.mp4", prefix="xiangjiao",
         vo="vo_xiangjiao.mp3",
         subs=["你天天吃的香蕉，植物学家说它是浆果！\\N而草莓，名字里带个莓，却根本不是浆果。",
               "植物学上，浆果是由一朵花的子房发育来的，\\N香蕉、葡萄、番茄、蓝莓都算。",
               "草莓是聚合瘦果，表面那些小籽才是真正的果实，\\N我们吃的红色果肉，其实是膨大的花托。",
               "下次吃草莓可以炫耀了：你吃的不是果，是花托！\\N你还被哪些水果的名字骗过？评论区聊聊！"]),
    dict(name="finished_小实验_铁水浇冰_竖版.mp4", prefix="tieshui",
         vo="vo_tieshui.mp3",
         subs=["一千五百多度的铁水倒在冰上，居然没有瞬间炸开？\\N注意，这是AI模拟演示，别在家模仿！",
               "铁的熔点高达一千五百三十八度，这团铁水超过一千五百度。",
               "铁水一碰到冰，接触面瞬间汽化，形成一层蒸汽垫，\\N把铁水托了起来。这就是莱顿弗罗斯特效应。",
               "蒸汽隔热，热量传不下去，铁水只能慢慢把冰融出一个坑。\\N现实里极度危险，看看模拟过过瘾就行！"]),
    dict(name="finished_小技巧1_去油渍_竖版.mp4", prefix="youzi",
         vo="vo_youzi.mp3",
         subs=["衣服沾上油渍，千万别直接扔洗衣机！\\N先在油渍上滴几滴洗洁精，干搓一分钟。",
               "注意，搓之前别沾水，水会把油封在纤维里。",
               "洗洁精里的表面活性剂专门乳化油脂，\\N比洗衣液去油猛多了。搓完静置几分钟，再正常机洗。",
               "记住两点：越快处理越好；真丝羊毛等娇贵面料，\\N先在不显眼的地方试试。你还知道哪些去渍神招？评论区聊聊！"]),
    dict(name="finished_小技巧2_热米饭_竖版.mp4", prefix="mifan",
         vo="vo_mifan.mp3",
         subs=["微波炉热出来的米饭又干又硬？那是你少做了一步！",
               "热之前，在米饭上洒几滴水，或者盖一张打湿的纸巾。",
               "补点水进去，蒸汽一循环，米饭就松软了，\\N跟刚蒸出来一样。盖盖子留缝也行，原理一样：锁住蒸汽。",
               "中火转两三分钟就够了，别贪多；\\N注意别用普通塑料碗，要用能进微波炉的。"]),
    dict(name="finished_帅哥美女_竖版.mp4", prefix="renxiang",
         vo=None, subs=["阳光治愈每一帧 ☀️"], title_only=True),
]

for v in VIDEOS:
    clips = clip_paths(v["prefix"])
    assert len(clips) == 4, f"{v['prefix']}: found {len(clips)} clips"
    durs = [probe_dur(c) for c in clips]
    cum = [0.0]
    for d in durs: cum.append(cum[-1] + d)
    out = os.path.join(BASE, v["name"])
    srt = os.path.join("/tmp", f"subs_{v['prefix']}.srt")
    if v.get("title_only"):
        write_srt(srt, [(0.0, 3.0, v["subs"][0])])
    else:
        vo_path = os.path.join(BASE, v["vo"])
        vo_dur = probe_dur(vo_path)
        bounds = [(cum[i], cum[i+1] if i < 3 else min(cum[i+1], vo_dur)) for i in range(4)]
        write_srt(srt, [(s, e, t) for (s, e), t in zip(bounds, v["subs"])])
    # filter_complex
    scales = "".join(f"[{i}:v]scale=1080:1920[v{i}];" for i in range(4))
    fc = (scales + "[v0][v1][v2][v3]concat=n=4:v=1:a=0,"
          f"subtitles={srt}:fontsdir={FONTSDIR}:force_style='{STYLE}'[v]")
    cmd = ["ffmpeg", "-y"]
    for c in clips: cmd += ["-i", c]
    if v["vo"]:
        cmd += ["-i", os.path.join(BASE, v["vo"])]
    cmd += ["-filter_complex", fc, "-map", "[v]"]
    if v["vo"]:
        cmd += ["-map", "4:a", "-c:a", "aac", "-b:a", "128k", "-shortest"]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", out]
    print("BUILD", v["name"], "clips:", [f"{d:.1f}s" for d in durs])
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("FAILED", v["name"]); print(r.stderr[-2000:]); break
    print("OK", out, f"{os.path.getsize(out)/1e6:.1f}MB")
print("DONE")
