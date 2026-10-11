#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成应用图标（渐变圆角 + 音符），输出 .ico / .png。"""
import os

from PIL import Image, ImageDraw

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "work")
os.makedirs(OUT, exist_ok=True)
S = 1024
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# 渐变底（紫 → 青绿），逐行插值
c1, c2 = (108, 92, 231), (0, 184, 148)
for y in range(S):
    t = y / (S - 1)
    col = (int(c1[0] + (c2[0] - c1[0]) * t),
           int(c1[1] + (c2[1] - c1[1]) * t),
           int(c1[2] + (c2[2] - c1[2]) * t), 255)
    d.line([(0, y), (S, y)], fill=col)
img = img.convert("RGBA")

# 圆角遮罩
mask = Image.new("L", (S, S), 0)
ImageDraw.Draw(mask).rounded_rectangle([0, 0, S - 1, S - 1], radius=int(S * 0.22), fill=255)
img.putalpha(mask)

# 音符（用圆 + 竖线 + 旗）
d = ImageDraw.Draw(img)
white = (255, 255, 255, 245)
cx, cy = int(S * 0.40), int(S * 0.72)
r = int(S * 0.105)
d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=white)                  # 符头
stem_w = int(S * 0.035)
d.rectangle([cx + r - stem_w, int(S * 0.24), cx + r, cy], fill=white)     # 符干
d.polygon([(cx + r, int(S * 0.24)), (cx + int(S * 0.30), int(S * 0.33)),
           (cx + int(S * 0.30), int(S * 0.45)), (cx + r, int(S * 0.37))], fill=white)  # 符旗
# 第二符头（双音符更好认）
cx2 = cx + int(S * 0.28)
d.ellipse([cx2 - r, cy - r, cx2 + r, cy + r], fill=white)
d.rectangle([cx2 + r - stem_w * 2, int(S * 0.34), cx2 + r - stem_w // 2, cy], fill=white)

img.save(os.path.join(OUT, "appicon.png"))
img.save(os.path.join(OUT, "appicon.ico"),
         sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128),
                (256, 256)])
print("已生成: work/appicon.ico 与 work/appicon.png (%dx%d)" % (S, S))
