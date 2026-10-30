#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查市面候选音源里，谁真的直连酷我（q 加密），谁只是转发第三方 API"""
import glob
import io
import os
import re

D = r"D:\project\kwlx\wy"
files = sorted(glob.glob(os.path.join(D, "*.js"))) + [r"D:\project\kwlx\kwlx-kuwo-source.js"]

SIGNS = {
    "mobi.kuwo.cn (酷我私有接口)": r"mobi\.kuwo\.cn",
    "ylzsxkwm (q 加密密钥)": r"ylzsxkwm",
    "convert_url2 (酷我换链)": r"convert_url2",
    "kwplayer_ar (伪装 App UA)": r"kwplayer_ar",
    "search.kuwo.cn (酷我搜索)": r"search\.kuwo\.cn",
    "m.kuwo.cn 歌词": r"m\.kuwo\.cn",
    "第三方聚合 API": r"oiapi\.net|gdstudio\.xyz|xcvts\.cn|nxinxz|huibq|lingchuan|vsaa|haitangw|sayqz",
}

print("%-26s %s" % ("文件", " | ".join(k.split()[0] for k in SIGNS)))
print("-" * 120)
for p in files:
    t = io.open(p, encoding="utf-8", errors="replace").read()
    row = []
    for name, pat in SIGNS.items():
        row.append("✓" if re.search(pat, t) else "·")
    print("%-26s %s   %s" % (os.path.basename(p), "   ".join(row), ""))
print()
print("图例: ✓=出现  ·=没有")
print()
print("=== 各文件的酷我直连证据（前 2 条）===")
for p in files:
    t = io.open(p, encoding="utf-8", errors="replace").read()
    hits = [m.group(0) for m in re.finditer(r"mobi\.kuwo\.cn[^\s\"'`]{0,40}", t)]
    if hits:
        print("  %-26s %s" % (os.path.basename(p), hits[:2]))
    else:
        hosts = sorted(set(re.findall(r"https?://([A-Za-z0-9.\-]+)", t)))
        print("  %-26s 无酷我直连；外链: %s" % (os.path.basename(p), ", ".join(hosts[:6]) or "(无)"))
