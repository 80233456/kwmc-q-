#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""行内下载按钮：去掉 download.enable 的门槛，始终显示"""
import io
import os
import re

SRC = r"D:\project\kwlx\lx-src"
p = os.path.join(SRC, "src/renderer/components/material/ListButtons.vue")
raw = io.open(p, "rb").read()
old = 'v-if="downloadBtn && appSetting[\'download.enable\']"'
new = 'v-if="downloadBtn"'
if old.encode("utf-8") in raw:
    raw = raw.replace(old.encode("utf-8"), new.encode("utf-8"))
    io.open(p, "wb").write(raw)
    print("✅ 已改为始终显示下载按钮")
else:
    # 退一步：用正则匹配任意空白差异
    txt = raw.decode("utf-8")
    m = re.search(r'v-if="downloadBtn[^"]*"', txt)
    print("未精确匹配，当前是:", m.group(0) if m else "(没找到 v-if=downloadBtn…)")
    if m and "download.enable" in m.group(0):
        txt = txt.replace(m.group(0), new, 1)
        io.open(p, "w", encoding="utf-8", newline="").write(txt)
        print("✅ 正则替换完成")

txt = io.open(p, encoding="utf-8").read()
for line in txt.splitlines():
    if "download" in line and "v-if" in line:
        print("  现在:", line.strip()[:110])
