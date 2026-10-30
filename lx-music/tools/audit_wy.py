#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""审计候选音源脚本：危险模式、外链主机、wy 解析逻辑"""
import io
import re
import sys

p = sys.argv[1] if len(sys.argv) > 1 else r"D:\project\kwlx\wy\quandou.js"
t = io.open(p, encoding="utf-8", errors="replace").read()
print("文件: %s" % p)
print("体积: %.1f KB, 行数: %d" % (len(t.encode()) / 1024, len(t.splitlines())))

print("\n=== 危险模式 ===")
patterns = [
    (r"\beval\s*\(", "eval"),
    (r"new\s+Function\s*\(", "new Function"),
    (r"atob\s*\(", "atob"),
    (r"localStorage", "localStorage"),
    (r"document\.cookie", "cookie"),
    (r"require\s*\(", "require"),
    (r"process\.", "process"),
    (r"\bfetch\s*\(", "fetch"),
    (r"XMLHttpRequest", "xhr"),
    (r"setInterval\s*\(", "setInterval"),
]
for pat, name in patterns:
    print("  %-14s %d" % (name, len(re.findall(pat, t))))

print("\n=== 外链主机 ===")
for h in sorted(set(re.findall(r"https?://([A-Za-z0-9.\-]+)", t))):
    print("  ", h)

print("\n=== 关键字出现次数 ===")
for k in ("wy", "163", "126.net", "flac", "lossless", "level", "quality"):
    print("  %-10s %d" % (k, t.count(k)))

print("\n=== 含 wy 或 163 的代码行（最多 25 行）===")
shown = 0
for i, line in enumerate(t.splitlines(), 1):
    if ("wy" in line or "163" in line) and shown < 25:
        s = line.strip()
        if len(s) > 4:
            print("%5d| %s" % (i, s[:200]))
            shown += 1
