#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 q 加密测试向量（Python 为基准），供 JS 版对拍。"""
import json
import os
import sys

sys.path.insert(0, r"D:\project\dsh-purge\re-baseapk")
from kuwo_q import encrypt_kuwo_query, decrypt_kuwo_query   # noqa: E402

CASES = [
    "user=0&corp=kuwo&source=kwplayer_ar_5.1.0.0_B_jiakong_vh.apk&p2p=1"
    "&type=convert_url2&sig=0&format=flac&rid=324244",
    "user=0&corp=kuwo&type=convert_url2&rid=28423286&format=mp3",
    "a",                      # 极短
    "12345678",               # 恰好 8 字节（一整个块，仍会补块）
    "1234567890123456",       # 16 字节
    "中文测试=酷我音乐",       # 多字节 UTF-8
    "user=0&corp=kuwo&source=kwplayer_ar_5.1.0.0_B_jiakong_vh.apk&p2p=1&type=lyric"
    "&songname=%E5%AF%8C%E5%A3%AB%E5%B1%B1%E4%B8%8B&artist=%E9%99%88%E5%A5%95%E8%BF%85"
    "&filename=&duration=259000&req=2&lrcx=1&rid=28423286&encode=utf8",
]

out = []
for p in CASES:
    q = encrypt_kuwo_query(p)
    back = decrypt_kuwo_query(q).rstrip(b"\x00").decode("utf-8")
    out.append({"plain": p, "q": q, "py_roundtrip": back})
    assert back == p, "Python 自身往返失败: %r" % p

path = r"D:\project\kwlx\vectors.json"
json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("已生成 %d 组向量 → %s" % (len(out), path))
for o in out[:2]:
    print("  plain=%s..." % o["plain"][:50])
    print("  q    =%s..." % o["q"][:60])
