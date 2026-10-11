#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
酷我音乐 纯 PC 下载管线（无需手机、无需破解版客户端）

流程：
    1) 关键词搜索            → search.kuwo.cn/r.s
    2) 取 rid
    3) 本地生成 q            → kuwo_q.py（自定义 DES，密钥 ylzsxkwm）
    4) mobi.s?f=kuwo&q=...  → 拿播放地址（优先 flac，其次 320kmp3）
    5) 下载并命名            → 歌名 - 歌手 [rid].flac
    6) 顺带取歌词（可选）

用法：
    python kuwo_pc_download.py "七里香"              # 搜索并下载第一首
    python kuwo_pc_download.py "七里香" --all        # 下载前 5 首
    python kuwo_pc_download.py --rid 228908          # 直接按 rid 下载
"""
import argparse
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kuwo_q import encrypt_kuwo_query

if getattr(sys, "frozen", False):          # 打包成 exe 时：放到用户音乐目录
    OUTDIR = os.path.join(os.path.expanduser("~"), "Music", "音乐盒Studio")
else:                                      # 源码运行时：放在项目 work 目录
    OUTDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "work", "pc_downloads")

# 歌词缓存：打包版放用户目录（单文件版解压目录每次运行都会重建）
if getattr(sys, "frozen", False):
    _USER_DIR = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"),
                             "MusicBoxStudio")
else:
    _USER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "work")
UA_OK = "okhttp/3.10.0"
UA_WEB = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36")
# 官方接口用的最小参数（musicdl / Groove 等社区项目一致）
CRED_MIN = ("user=0&corp=kuwo&source=kwplayer_ar_5.1.0.0_B_jiakong_vh.apk&p2p=1")


def http(url, headers=None, timeout=30, read=None):
    hdr = {"User-Agent": UA_WEB}
    hdr.update(headers or {})
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=hdr),
                                    timeout=timeout) as r:
            return r.status, dict(r.headers), r.read(read) if read else r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), b""
    except Exception as e:
        return -1, {}, str(e).encode()[:200]


def _field(item, key, default=""):
    """从一段 '{"KEY":"value",...}' 文本里取值；容忍值里混有未转义引号。"""
    m = re.search(r'"%s"\s*:\s*"((?:[^"\\]|\\.)*)"\s*[,\}]' % re.escape(key), item)
    if m:
        return m.group(1)
    m = re.search(r'"%s"\s*:\s*"([^"]*)' % re.escape(key), item)
    return m.group(1) if m else default


def _split_abslist(txt):
    """把响应里的 abslist 数组切成一条条 item 文本（容错，不依赖合法 JSON）。"""
    i = txt.find('"abslist"')
    if i < 0:
        return []
    j = txt.find("[", i)
    if j < 0:
        return []
    body = txt[j + 1:]
    items, depth, start, k = [], 0, None, 0
    while k < len(body):
        c = body[k]
        if c == "{":
            if depth == 0:
                start = k
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0 and start is not None:
                items.append(body[start:k + 1])
                start = None
        elif c == "]" and depth == 0:
            break
        k += 1
    return items


def search(keyword, page=1, size=20):
    """返回 [{rid, name, artist, album, duration}]（容错解析，兼容嵌套 abslist）。"""
    url = ("http://search.kuwo.cn/r.s?all=%s&pn=%d&rn=%d&reqId=85bde120-b7b5-11ec-94ee-75d538904202"
           "&client=kt&uid=794762570&ver=kwplayer_ar_9.2.2.1&vipver=1&show_copyright_off=1"
           "&newver=1&ft=music&cluster=0&strategy=2012&encoding=utf8&rformat=json&vermerge=1"
           "&mobi=1&issubtitle=1" % (urllib.parse.quote(keyword), page - 1, size))
    st, _, body = http(url, {"User-Agent": UA_WEB}, read=400000)
    txt = body.decode("utf-8", "replace")

    out, seen = [], set()

    def push(name, artist, rid, album, dur, pic_short="", minfo="", pay=""):
        rid = str(rid or "").replace("MUSIC_", "").strip()
        if not rid or not name or rid in seen:
            return
        seen.add(rid)
        best = ""
        for m in re.finditer(r"level:(\w+),bitrate:(\d+),format:(\w+),size:([\d.]+)(Mb|Kb)",
                             minfo or ""):
            best = "%s %s" % (m.group(3).upper(), m.group(4) + m.group(5)[:1])
            if m.group(1) == "ff":
                break
        out.append({"rid": rid,
                    "name": html.unescape(name).replace("&nbsp;", " ").strip(),
                    "artist": html.unescape(artist or "").strip(),
                    "album": html.unescape(album or "").strip(),
                    "duration": dur,
                    "pic_short": pic_short or "",
                    "minsize": best,
                    "pay": str(pay or "")})

    # 1) 先试严格 JSON（保序遍历：先 abslist，再其它嵌套）
    try:
        data = json.loads(txt)

        def walk(node):
            if isinstance(node, dict):
                if node.get("MUSICRID") or node.get("musicrid"):
                    push(node.get("SONGNAME") or node.get("NAME") or node.get("name"),
                         node.get("ARTIST") or node.get("artist"),
                         node.get("MUSICRID") or node.get("musicrid"),
                         node.get("ALBUM") or node.get("album"),
                         node.get("DURATION") or node.get("duration"),
                         node.get("web_albumpic_short") or "",
                         node.get("MINFO") or "",
                         node.get("PAY") or node.get("pay") or "")
                if isinstance(node.get("abslist"), list):
                    for x in node["abslist"]:
                        walk(x)
                for k, v in node.items():
                    if k != "abslist" and isinstance(v, (dict, list)):
                        walk(v)
            elif isinstance(node, list):
                for x in node:
                    walk(x)

        walk(data)
        if out:
            return out
    except Exception:
        pass

    # 2) 容错：按条目扫描
    for item in _split_abslist(txt):
        name = _field(item, "SONGNAME") or _field(item, "NAME") or _field(item, "name")
        push(name,
             _field(item, "ARTIST") or _field(item, "artist"),
             _field(item, "MUSICRID") or _field(item, "musicrid"),
             _field(item, "ALBUM") or _field(item, "album"),
             _field(item, "DURATION") or _field(item, "duration"),
             _field(item, "web_albumpic_short"),
             _field(item, "MINFO"),
             _field(item, "PAY") or _field(item, "pay"))
    return out


def resolve_url(rid, fmt="flac", br=None, timeout=25):
    """用自制 q 请求播放地址；返回 (url, format, bitrate) 或 (None, None, None)"""
    parts = ["type=convert_url2", "sig=0", "format=%s" % fmt]
    if br:
        parts.append("br=%s" % br)
    parts.append("rid=%s" % rid)
    plain = CRED_MIN + "&" + "&".join(parts)
    q = encrypt_kuwo_query(plain)
    st, _, body = http("http://mobi.kuwo.cn/mobi.s?f=kuwo&q=" + q,
                       {"User-Agent": UA_OK}, timeout=timeout, read=4096)
    txt = body.decode("utf-8", "replace")
    m = re.search(r"url=(http\S+)", txt)
    if not m:
        return None, None, None
    f = re.search(r"format=(\w+)", txt)
    b = re.search(r"bitrate=(\d+)", txt)
    return m.group(1), (f.group(1) if f else fmt), (b.group(1) if b else "")


def remote_size(url):
    st, hdr, _ = http(url, {"User-Agent": UA_OK, "Range": "bytes=0-1"}, timeout=20)
    cr = hdr.get("Content-Range") or ""
    m = re.search(r"/(\d+)$", cr)
    if m:
        return int(m.group(1))
    try:
        return int(hdr.get("Content-Length") or 0)
    except Exception:
        return 0


def download(url, path, chunk=1 << 20):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": UA_OK})
    total = 0
    with urllib.request.urlopen(req, timeout=60) as r, open(path, "wb") as f:
        while True:
            b = r.read(chunk)
            if not b:
                break
            f.write(b)
            total += len(b)
    return total


def safe_name(s):
    return re.sub(r'[\\/:*?"<>|]', "_", s).strip() or "unknown"


UA_MOBILE = ("Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 (KHTML, like Gecko) "
             "Chrome/120.0 Mobile Safari/537.36")
H5_HDR = {"User-Agent": UA_MOBILE, "Referer": "https://m.kuwo.cn/",
          "Accept": "application/json, text/plain, */*"}
LYRIC_CACHE = os.path.join(_USER_DIR, "lyrics")


def _parse_lrclist(txt):
    """H5 接口的 {'data':{'lrclist':[{'time','lineLyric'}]}} → LRC 文本。"""
    try:
        data = json.loads(txt)
    except Exception:
        return None
    lst = (data.get("data") or {}).get("lrclist") or []
    if not lst:
        return None
    out = []
    for it in lst:
        t = float(it.get("time") or 0)
        out.append("[%02d:%02d.%02d]%s" % (int(t // 60), int(t % 60),
                                           int(round((t - int(t)) * 100)),
                                           it.get("lineLyric") or ""))
    return "\n".join(out)


def _netease_lyric(name, artist):
    """第三方兜底：网易云按歌名+歌手搜索后取词（酷我接口全挂时用）。"""
    try:
        q = urllib.parse.quote(("%s %s" % (name, artist)).strip())
        st, _h, body = http("https://music.163.com/api/search/get?s=%s&type=1&limit=5" % q,
                            {"User-Agent": UA_WEB, "Referer": "https://music.163.com/"},
                            timeout=20, read=300000)
        songs = (json.loads(body.decode("utf-8", "replace")).get("result") or {}).get("songs") or []
        for s in songs:
            if not s.get("id"):
                continue
            st, _h, b2 = http("https://music.163.com/api/song/lyric?id=%s&lv=-1&kv=-1&tv=-1"
                              % s["id"],
                              {"User-Agent": UA_WEB, "Referer": "https://music.163.com/"},
                              timeout=20, read=400000)
            lrc = (json.loads(b2.decode("utf-8", "replace")).get("lrc") or {}).get("lyric") or ""
            if re.search(r"\[\d+:\d+(?:\.\d+)?\]", lrc):
                return lrc
    except Exception:
        pass
    return None


def fetch_lyric(rid, name="", artist="", duration_ms=0, use_cache=True):
    """取歌词（多级降级 + 磁盘缓存）。

    顺序：缓存 → H5(http,实测可用) → H5(https) → App 加密通道 → 网易云兜底。
    注：duration 传秒也行（<10000 自动按秒换算）。
    """
    rid = str(rid or "")
    cache_file = os.path.join(LYRIC_CACHE, "%s.lrc" % rid) if rid else ""
    if use_cache and cache_file and os.path.exists(cache_file):
        try:
            txt = open(cache_file, encoding="utf-8").read()
            if txt.strip():
                return txt
        except Exception:
            pass
    try:
        duration_ms = int(float(duration_ms or 0))
    except Exception:
        duration_ms = 0
    if 0 < duration_ms < 10000:                  # 秒 → 毫秒
        duration_ms *= 1000

    def done(lrc):
        if lrc and cache_file:
            try:
                os.makedirs(LYRIC_CACHE, exist_ok=True)
                with open(cache_file, "w", encoding="utf-8") as fh:
                    fh.write(lrc)
            except Exception:
                pass
        return lrc

    # 1) 酷我 H5：**http** 可用，https 会被限流（实测）
    for url in ("http://m.kuwo.cn/newh5/singles/songinfoandlrc?musicId=%s" % rid,
                "https://m.kuwo.cn/newh5/singles/songinfoandlrc?musicId=%s" % rid):
        if not rid:
            break
        try:
            st, _h, body = http(url, H5_HDR, timeout=20, read=300000)
            lrc = _parse_lrclist(body.decode("utf-8", "replace"))
            if lrc:
                return done(lrc)
        except Exception:
            pass

    # 2) App 同款加密通道（部分曲目该通道返回加密载荷 → 校验不通过会自动跳过）
    if rid:
        try:
            from kuwo_q import encrypt_kuwo_query
            plain = (CRED_MIN + "&type=lyric&songname=%s&artist=%s&filename=&duration=%d"
                     "&req=2&lrcx=1&rid=%s&encode=utf8"
                     % (urllib.parse.quote(name or ""), urllib.parse.quote(artist or ""),
                        int(duration_ms or 0), rid))
            st, _h, body = http("http://mobi.kuwo.cn/mobi.s?f=kuwo&q=" + encrypt_kuwo_query(plain),
                                {"User-Agent": UA_OK}, timeout=25, read=600000)
            if body.startswith(b"TP=content"):
                payload = body.split(b"\r\n\r\n", 1)[1]
                if payload[:1] == b"\x78":
                    payload = zlib.decompress(payload)
                txt = payload.decode("utf-8", "replace")
                if re.search(r"\[\d+:\d+(?:\.\d+)?\]", txt):
                    return done(txt)
        except Exception:
            pass

    # 3) 第三方兜底
    if name:
        lrc = _netease_lyric(name, artist)
        if lrc:
            return done(lrc)
    return None


def process(rid, name=None, artist=None, want_lyric=True):
    print("\n>>> rid=%s %s %s" % (rid, name or "", artist or ""))
    best = None
    for fmt, br in (("flac", "2000kflac"), ("flac", None), ("mp3", "320kmp3"), ("mp3", "128kmp3")):
        u, f, b = resolve_url(rid, fmt, br)
        if not u:
            print("    %-6s br=%-10s → 无地址" % (fmt, br or "-"))
            continue
        size = remote_size(u)
        print("    %-6s br=%-10s → %s  %.1f MB" % (fmt, br or "-", f,
                                                size / 1048576 if size else 0))
        if size > 1_000_000:            # 大于 1MB 视为可用完整曲目
            best = (u, f, size)
            break
    if not best:
        print("    × 没有拿到可用完整地址（可能是会员限制曲目）")
        return None
    u, f, size = best
    fn = "%s - %s [%s].%s" % (safe_name(name or rid), safe_name(artist or ""), rid, f)
    path = os.path.join(OUTDIR, fn)
    print("    下载 → %s" % path)
    n = download(u, path)
    print("    完成 %.1f MB" % (n / 1048576))
    # 按内嵌标签正式命名（最可靠，且能修掉搜索名里的杂项）
    if f == "flac":
        t = flac_tags(path)
        tn, ta = t.get("title"), t.get("artist")
        if tn:
            new_fn = "%s - %s [%s].flac" % (safe_name(tn), safe_name(ta or ""), rid)
            new_path = os.path.join(OUTDIR, new_fn)
            if os.path.abspath(new_path) != os.path.abspath(path):
                os.replace(path, new_path)
                print("    已按内嵌标签重命名 → %s" % new_fn)
                path = new_path
    if want_lyric:
        lrc = fetch_lyric(rid)
        if lrc:
            open(path.rsplit(".", 1)[0] + ".lrc", "w", encoding="utf-8").write(lrc)
            print("    歌词已保存")
    return path


def flac_tags(path):
    """读 FLAC 内嵌 Vorbis Comment，用于给文件正式命名。"""
    try:
        with open(path, "rb") as f:
            if f.read(4) != b"fLaC":
                return {}
            while True:
                hdr = f.read(4)
                if len(hdr) < 4:
                    return {}
                last, btype = hdr[0] >> 7, hdr[0] & 0x7F
                size = int.from_bytes(hdr[1:4], "big")
                data = f.read(size)
                if btype == 4:
                    pos = 4
                    vlen = int.from_bytes(data[0:4], "little")
                    pos += vlen
                    n = int.from_bytes(data[pos:pos + 4], "little")
                    pos += 4
                    tags = {}
                    for _ in range(n):
                        l = int.from_bytes(data[pos:pos + 4], "little")
                        pos += 4
                        kv = data[pos:pos + l].decode("utf-8", "replace")
                        pos += l
                        if "=" in kv:
                            k, v = kv.split("=", 1)
                            tags[k.lower()] = v
                    return tags
                if last:
                    return {}
    except Exception:
        return {}


def meta_by_rid(rid, tries=3):
    """--rid 模式：从 h5app 接口补歌名/歌手（H5 singles 接口有限流，故用 wapi）。"""
    for i in range(tries):
        st, _, body = http("https://m.kuwo.cn/newh5app/wapi/api/www/music/musicInfo?mid=%s" % rid,
                           read=20000)
        try:
            d = (json.loads(body.decode("utf-8", "replace").strip()).get("data") or {})
            name = d.get("name") or d.get("songName")
            if name:
                return name, d.get("artist")
        except Exception:
            pass
        time.sleep(1.2 * (i + 1))
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("keyword", nargs="?", help="搜索关键词")
    ap.add_argument("--rid", help="直接指定 rid")
    ap.add_argument("--all", action="store_true", help="下载搜索结果的前 5 首")
    ap.add_argument("--no-lyric", action="store_true")
    a = ap.parse_args()
    os.makedirs(OUTDIR, exist_ok=True)
    if a.rid:
        name, artist = meta_by_rid(a.rid)
        print("rid=%s → %s / %s" % (a.rid, name, artist))
        process(a.rid, name, artist, want_lyric=not a.no_lyric)
        return 0
    if not a.keyword:
        ap.print_help()
        return 1
    print("搜索：%s" % a.keyword)
    res = search(a.keyword)
    if not res:
        print("搜索无结果")
        return 1
    for i, it in enumerate(res[:10], 1):
        print("  %2d. %-30s %-20s rid=%s" % (i, it["name"][:30], it["artist"][:20], it["rid"]))
    todo = res[:5] if a.all else res[:1]
    ok = 0
    for it in todo:
        if process(it["rid"], it["name"], it["artist"], not a.no_lyric):
            ok += 1
    print("\n完成 %d/%d" % (ok, len(todo)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
