#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把各页截图拼成一张总览图（带标题），便于快速审阅 UI。"""
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(HERE, "ui_shots")
PAGES = [("app_search.png", "搜索结果：封面 / VIP 徽标 / 试听·下载按钮"),
         ("app_lyrics.png", "歌词页：平滑滚动 + 卡拉OK 渐变 + 点击跳转"),
         ("app_library.png", "本地曲库：FLAC/MP3 区分、双击播放"),
         ("app_queue.png", "下载队列：真实进度、完成后清理"),
         ("app_settings.png", "设置：下载目录 / 播放 / 缓存与关于"),
         ("app_empty.png", "空状态：图标 + 标题 + 提示")]

COL, ROW = 2, 3
TW = 660                      # 每格宽度
PAD, TITLE_H = 22, 34
try:
    F = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 19)
    F2 = ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 26)
except Exception:
    F = F2 = ImageFont.load_default()

tiles = []
for name, cap in PAGES:
    p = os.path.join(SHOTS, name)
    im = Image.open(p).convert("RGB")
    th = int(TW * im.height / im.width)
    tiles.append((im.resize((TW, th), Image.LANCZOS), cap))

TH = tiles[0][0].height
W = COL * TW + PAD * (COL + 1)
H = TITLE_H + ROW * (TH + TITLE_H) + PAD * (ROW + 1) + 46
canvas = Image.new("RGB", (W, H), (11, 13, 17))
d = ImageDraw.Draw(canvas)
d.text((PAD, 14), "音乐盒 Studio · 界面总览（UI 检查与优化后）", font=F2, fill=(230, 232, 238))
for i, (im, cap) in enumerate(tiles):
    r, c = divmod(i, COL)
    x = PAD + c * (TW + PAD)
    y = TITLE_H + 40 + r * (TH + TITLE_H) + PAD
    canvas.paste(im, (x, y))
    d.rectangle([x, y, x + TW - 1, y + im.height], outline=(35, 39, 51))
    d.text((x + 2, y + im.height + 8), cap, font=F, fill=(139, 147, 167))
out = os.path.join(SHOTS, "overview.png")
canvas.save(out)
print("总览图 →", out, canvas.size)
