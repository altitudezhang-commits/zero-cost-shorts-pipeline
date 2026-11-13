#!/usr/bin/env python3
"""混合素材路线：Wikimedia Commons 免 key 检索真实图片，版权干净的才收。

用法：
  python3 fetch_footage.py --out <输出目录> queries.json

queries.json 格式：
  {"seg0": ["semiconductor wafer close-up", "silicon wafer"],
   "seg1": ["ASML lithography", ...], ...}

输出（<out>/）：
  segN.jpg/png        下载的原图（仅 status=real 的段）
  manifest.json       每段 {status, clip_path, title, author, license, source_url, motion}
                      + attribution 文本块（英文固定格式）
  attribution.txt     可直接贴进视频简介的署名块

版权规则：只收 CC BY / CC BY-SA / CC0 / Public Domain；
凡带 NC（非商业）或 ND（禁演绎）的全部排除。
搜不到可用图（0 结果或全被版权/尺寸过滤）→ 该段 status=fallback，
cron worker 对该段改用 media.generate_video 生成 AI 片段。
"""
import json, os, re, sys, time, html
import urllib.request, urllib.parse

UA = {"User-Agent": "yt-science-shorts/1.0 (educational use; contact: channel owner)"}
API = "https://commons.wikimedia.org/w/api.php"
MIN_W = 800                      # 竖屏裁切至少要这个宽度
ACCEPT_MIMES = {"image/jpeg", "image/png"}

def api_get(params, timeout=25):
    q = urllib.parse.urlencode(params)
    req = urllib.request.Request(API + "?" + q, headers=UA)
    for attempt in (1, 2):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except Exception as e:
            if attempt == 2:
                raise
            time.sleep(2)
    raise RuntimeError("unreachable")

def strip_html(s):
    return re.sub(r"<[^>]+>", "", html.unescape(s or "")).strip()

def license_ok(short):
    """只接受可商用、可演绎的协议。"""
    s = (short or "").upper()
    if "NC" in s or "ND" in s:
        return False
    return ("CC BY" in s) or ("PUBLIC DOMAIN" in s) or ("CC0" in s)

def search_files(query):
    d = api_get({
        "action": "query", "format": "json",
        "generator": "search", "gsrsearch": f"{query} filetype:bitmap",
        "gsrnamespace": "6", "gsrlimit": "20",
        "prop": "imageinfo",
        "iiprop": "url|size|mime|extmetadata",
        "iiextmetadatafilter": "LicenseShortName|Artist",
    })
    return list(((d.get("query") or {}).get("pages") or {}).values())

def pick_candidate(pages):
    for p in pages:
        ii = (p.get("imageinfo") or [{}])[0]
        if ii.get("mime") not in ACCEPT_MIMES:
            continue
        if (ii.get("width") or 0) < MIN_W:
            continue
        meta = ii.get("extmetadata") or {}
        lic = strip_html((meta.get("LicenseShortName") or {}).get("value", ""))
        if not license_ok(lic):
            continue
        artist = strip_html((meta.get("Artist") or {}).get("value", "")) or "Unknown"
        url = ii.get("url")
        if not url:
            continue
        title = p.get("title", "")
        page = "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))
        return {"title": title, "author": artist, "license": lic,
                "file_url": url, "source_url": page,
                "mime": ii["mime"], "width": ii.get("width")}
    return None

def download(url, dest):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
        total = 0
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            total += len(chunk)
            if total > 60 * 1024 * 1024:   # 单张 60MB 上限
                raise RuntimeError("file too large")
    return total

MOTIONS = ["zoomin", "panright", "zoomout", "panleft"]

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("queries", help="queries.json 路径")
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)

    with open(a.queries, encoding="utf-8") as f:
        queries = json.load(f)

    manifest = {"segments": {}, "attribution": ""}
    attr_lines = []
    for i, seg in enumerate(sorted(queries.keys())):
        entry = {"status": "fallback"}
        cand = None
        for q in queries[seg]:
            try:
                pages = search_files(q)
            except Exception as e:
                print(f"{seg}: search error for {q!r}: {e}", flush=True)
                continue
            cand = pick_candidate(pages)
            if cand:
                print(f"{seg}: picked {cand['title'][:60]} [{cand['license']}] via {q!r}", flush=True)
                break
        if cand:
            ext = ".jpg" if cand["mime"] == "image/jpeg" else ".png"
            fname = f"{seg}{ext}"
            dest = os.path.join(out, fname)
            try:
                nbytes = download(cand["file_url"], dest)
            except Exception as e:
                print(f"{seg}: download failed: {e} -> fallback", flush=True)
            else:
                motion = MOTIONS[i % len(MOTIONS)]
                entry = {"status": "real", "clip_path": dest,
                         "title": cand["title"], "author": cand["author"],
                         "license": cand["license"], "source_url": cand["source_url"],
                         "bytes": nbytes, "motion": motion}
                attr_lines.append(
                    f'{seg}: "{cand["title"]}" by {cand["author"]}, {cand["license"]}, {cand["source_url"]}')
        else:
            print(f"{seg}: no usable image -> fallback (AI generate)", flush=True)
        manifest["segments"][seg] = entry

    manifest["attribution"] = "Footage/images: " + " | ".join(attr_lines) if attr_lines else ""
    with open(os.path.join(out, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    with open(os.path.join(out, "attribution.txt"), "w", encoding="utf-8") as f:
        f.write(manifest["attribution"] + "\n")

    n_real = sum(1 for s in manifest["segments"].values() if s["status"] == "real")
    print(f"done: {n_real}/{len(manifest['segments'])} segments real, manifest -> {out}/manifest.json")

if __name__ == "__main__":
    main()
