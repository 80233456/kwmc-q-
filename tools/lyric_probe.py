#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""歌词备选端点全测：找出稳定可用的取词方式（含请求头组合、第三方兜底）。"""
import json
import sys
import urllib.parse

sys.path.insert(0, ".")
from kuwo_pc_download import http

RID, NAME, ARTIST = "28423286", "富士山下", "陈奕迅"
UA_MOBILE = ("Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 (KHTML, like Gecko) "
             "Chrome/120.0 Mobile Safari/537.36")
UA_WEB = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
          "Chrome/122.0 Safari/537.36")
H5 = {"User-Agent": UA_MOBILE, "Referer": "https://m.kuwo.cn/",
      "Accept": "application/json, text/plain, */*"}
WEB = {"User-Agent": UA_WEB, "Referer": "https://www.kuwo.cn/",
       "Accept": "application/json, text/plain, */*", "csrf": ""}


def try_url(tag, url, hdr, picker):
    try:
        st, _h, body = http(url, hdr, timeout=20, read=400000)
        txt = body.decode("utf-8", "replace").strip()
        got = picker(txt)
        print("  %-30s HTTP %-4s %s" % (tag, st, ("✓ " + got) if got else ("✗ " + txt[:90])))
        return got
    except Exception as e:
        print("  %-30s 异常 %s" % (tag, str(e)[:70]))
        return None


def pick_lrc(txt):
    if txt.startswith("[") and "]" in txt[:20]:
        return "LRC %d 行，首行 %s" % (len(txt.splitlines()), txt.splitlines()[0][:34])
    try:
        d = json.loads(txt)
        lst = (d.get("data") or {}).get("lrclist") or []
        if lst:
            return "JSON lrclist %d 行，首句 %s" % (len(lst), (lst[0].get("lineLyric") or "")[:24])
    except Exception:
        pass
    return None


print("=== A. 酷我 H5（带手机 UA + Referer）===")
try_url("singles/songinfoandlrc", "https://m.kuwo.cn/newh5/singles/songinfoandlrc?musicId=%s" % RID,
        H5, pick_lrc)
try_url("newh5app v1 music/songinfoandlrc",
        "https://m.kuwo.cn/newh5app/api/mobile/v1/music/songinfoandlrc?musicId=%s" % RID,
        H5, pick_lrc)
try_url("HTTP 版本", "http://m.kuwo.cn/newh5/singles/songinfoandlrc?musicId=%s" % RID, H5, pick_lrc)

print("\n=== B. 网页版接口 ===")
try_url("api/v1 www lyric",
        "https://www.kuwo.cn/api/v1/www/music/lyric?musicId=%s&httpsStatus=1" % RID, WEB, pick_lrc)
try_url("api/www 免登录 lyric",
        "https://www.kuwo.cn/api/www/music/lyric?musicId=%s&httpsStatus=1" % RID, WEB, pick_lrc)

print("\n=== C. 老歌词 CDN ===")
for u in ("http://newlyric.kuwo.cn/newlyric.lrc?musicId=%s" % RID,
          "http://newlyric.kuwo.cn/newlyric.lrc?%s" % urllib.parse.urlencode(
              {"musicId": RID, "corp": "kuwo", "k": ""}),
          "http://newlyric.kuwo.cn/newlyric.lrc?rid=%s" % RID):
    try_url(u.split("?")[0][-24:] + "?" + u.split("?")[1][:22], u, H5, pick_lrc)

print("\n=== D. 第三方兜底：网易云（按歌名+歌手搜索再取词）===")
try:
    st, _h, body = http(
        "https://music.163.com/api/search/get?s=%s&type=1&limit=3"
        % urllib.parse.quote("%s %s" % (NAME, ARTIST)),
        {"User-Agent": UA_WEB, "Referer": "https://music.163.com/"}, read=300000)
    d = json.loads(body.decode("utf-8", "replace"))
    songs = (d.get("result") or {}).get("songs") or []
    print("  搜索到 %d 首：%s" % (len(songs),
                               [(s["name"], s["artists"][0]["name"]) for s in songs[:2]]))
    if songs:
        sid = songs[0]["id"]
        st, _h, b2 = http("https://music.163.com/api/song/lyric?id=%s&lv=-1&kv=-1&tv=-1" % sid,
                          {"User-Agent": UA_WEB, "Referer": "https://music.163.com/"},
                          read=400000)
        d2 = json.loads(b2.decode("utf-8", "replace"))
        lrc = (d2.get("lrc") or {}).get("lyric") or ""
        n = len([x for x in lrc.splitlines() if x.strip()])
        print("  歌词 %d 行  首行: %s" % (n, (lrc.splitlines()[0][:40] if n else "-")))
except Exception as e:
    print("  异常:", str(e)[:120])
