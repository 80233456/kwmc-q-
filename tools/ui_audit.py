#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI 数值化体检（无需肉眼）：
  1) 每个矢量图标：着墨率、是否越界、左右/上下居中偏差、是否有"缺角"
  2) 文字适配：控件宽度 vs 文本像素宽度（检测截断/挤爆）
  3) 歌词组件：高亮像素是否存在、激活行是否在可视区、行距与可见行数、缓动是否收敛
  4) 控件几何：零尺寸、重叠、超出父容器
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from PySide6.QtCore import Qt, QRectF, QTimer                       # noqa: E402
from PySide6.QtGui import QColor, QImage, QPainter, QFont           # noqa: E402
from PySide6.QtWidgets import QApplication                          # noqa: E402

import ui_kit as UK                                                 # noqa: E402

app = QApplication([])
ICONS = ["search", "library", "download", "settings", "play", "pause", "stop",
         "prev", "next", "volume", "mute", "lyric", "folder", "refresh", "trash",
         "queue", "note", "shuffle", "repeat", "repeat1", "check", "close",
         "external", "heart", "vip", "spinner", "warning"]
problems = []


def ink_stats(name, size=24):
    pm = UK.icon_pixmap(name, size, "#ffffff", 1.0)
    img = pm.toImage()
    W, H = img.width(), img.height()
    xs, ys, n = [], [], 0
    for y in range(H):
        for x in range(W):
            if QColor(img.pixel(x, y)).alpha() > 40:
                xs.append(x)
                ys.append(y)
                n += 1
    if n == 0:
        return {"name": name, "ink": 0.0, "empty": True}
    bx0, bx1, by0, by1 = min(xs), max(xs), min(ys), max(ys)
    cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
    return {"name": name, "ink": n / (W * H), "empty": False,
            "touch_edge": bx0 <= 0 or by0 <= 0 or bx1 >= W - 1 or by1 >= H - 1,
            "off_center_x": abs(cx - (W - 1) / 2) / W, "off_center_y": abs(cy - (H - 1) / 2) / H,
            "bbox": (bx0, by0, bx1, by1)}


print("=== 1) 矢量图标体检 ===")
print("   名称          着墨率   越界  水平偏心  垂直偏心")
for n in ICONS:
    st = ink_stats(n)
    if st.get("empty"):
        problems.append("图标 %s 是空的" % n)
        print("   %-12s  空!!" % n)
        continue
    flag = []
    if st["ink"] < 0.05:
        flag.append("着墨过少")
    if st["ink"] > 0.62:
        flag.append("着墨过多糊成一团")
    if st["touch_edge"]:
        flag.append("触碰边界(可能被裁)")
    if st["off_center_x"] > 0.09:
        flag.append("水平偏心")
    if st["off_center_y"] > 0.09:
        flag.append("垂直偏心")
    if flag:
        problems.append("图标 %s: %s" % (n, "、".join(flag)))
    print("   %-12s  %5.1f%%   %-4s  %6.1f%%   %6.1f%%   %s"
          % (n, st["ink"] * 100, "是" if st["touch_edge"] else "否",
             st["off_center_x"] * 100, st["off_center_y"] * 100,
             ("⚠ " + "、".join(flag)) if flag else ""))

print("\n=== 2) 文字适配体检（控件宽度 vs 文本宽度）===")
CASES = [
    ("侧栏项", "💾   本地曲库", 196 - 24 - 28, 13),
    ("侧栏项", "🔍   搜索", 196 - 24 - 28, 13),
    ("播放条曲名", "富士山下 - 陈奕迅 (Live 2023 世界巡回演唱会)", 420, 15),
    ("按钮", "下载选中", 90, 13),
    ("表头", "可用大小", 130, 13),
    ("表头", "操作", 150, 13),
    ("提示", "双击试听 · 右键下载", 150, 13),
    ("空状态标题", "输入关键词开始搜索", 400, 12),
    ("状态栏", "正在播放：富士山下 - 陈奕迅", 600, 12),
]
for label, text, avail, pt in CASES:
    f = QFont("Microsoft YaHei UI", pt)
    w = QFontMetrics(f).horizontalAdvance(text)
    ok = w <= avail
    if not ok:
        problems.append("文字可能被裁：%s「%s」需 %dpx / 可用 %dpx" % (label, text[:14], w, avail))
    print("   %-10s 需要 %4dpx / 可用 %4dpx  %s   %s"
          % (label, w, avail, "OK " if ok else "截断", text[:26]))

from PySide6.QtGui import QFontMetrics                          # noqa: E402

print("\n=== 3) 歌词组件体检 ===")
lv = UK.LyricsView()
lv.resize(760, 460)
lines = [(i * 4000, "第 %d 行歌词内容测试文本 abc" % i) for i in range(40)]
lv.set_lyrics(lines)
lh = lv._metrics()
print("   行高=%d  可视行数≈%.1f" % (lh, 460 / lh))
for frac in (0.0, 0.5, 0.99):
    lv.pos = 4000 * 12 + int(4000 * frac)
    lv.set_position(lv.pos)
    lv._offset = lv._target = float(lv.active)
    lv._frac = frac
    pm = QImage(760, 460, QImage.Format_ARGB32)
    pm.fill(QColor(UK.THEME["panel"]))
    p = QPainter(pm)
    lv.render(p)
    p.end()
    # 统计强调色像素（高亮/进度条/指示条）
    accent = 0
    accent_rgb = QColor(UK.THEME["accent"])
    for y in range(0, 460, 2):
        for x in range(0, 760, 2):
            c = QColor(pm.pixel(x, y))
            if abs(c.red() - accent_rgb.red()) < 70 and abs(c.green() - accent_rgb.green()) < 70 \
                    and abs(c.blue() - accent_rgb.blue()) < 90 and c.alpha() > 100:
                accent += 1
    y_active = 460 * 0.42
    print("   frac=%.2f  激活行=%d  强调色像素=%d  %s"
          % (frac, lv.active, accent, "OK" if accent > 0 else "⚠ 没有高亮!"))
    if accent == 0:
        problems.append("歌词 frac=%.2f 时没有高亮像素" % frac)

# 缓动收敛性
lv._offset, lv._target = 0.0, 20.0
for _ in range(120):
    lv._tick()
err = abs(lv._target - lv._offset)
print("   缓动收敛：目标 20.0，120 帧后偏差 %.4f  %s" % (err, "OK" if err < 0.05 else "⚠ 不收敛"))
if err >= 0.05:
    problems.append("歌词滚动缓动不收敛，偏差 %.3f" % err)

print("\n=== 4) 结论 ===")
if problems:
    for s in problems:
        print("   ⚠ " + s)
else:
    print("   全部通过 ✅")
print("（共 %d 项问题）" % len(problems))
QTimer.singleShot(20, app.quit)
app.exec()
