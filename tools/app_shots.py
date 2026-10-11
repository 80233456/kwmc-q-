#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""整窗截图（真实数据）：搜索页 / 歌词页 / 曲库页 / 队列页 / 设置页 + 空状态。"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from PySide6.QtCore import QTimer                                  # noqa: E402
from PySide6.QtWidgets import QApplication                         # noqa: E402

import kuwo_app as A                                               # noqa: E402

OUT = os.path.join(ROOT, "work", "ui_shots")
os.makedirs(OUT, exist_ok=True)
app = QApplication(sys.argv)
app.setStyleSheet(A.QSS)
w = A.Studio()
w.resize(1360, 880)
w.move(-4000, -4000)
w.show()


def pump(sec):
    t0 = time.time()
    while time.time() - t0 < sec:
        app.processEvents()
        time.sleep(0.02)


def grab(name):
    pm = w.grab()
    pm.save(os.path.join(OUT, name))
    print("%-22s %dx%d" % (name, pm.width(), pm.height()))


steps = []


def run():
    pump(1.0)
    grab("app_empty.png")             # 空状态（搜索页初始）
    w.ed_search.setText("富士山下 陈奕迅")
    w.do_search()
    pump(14)                          # 等搜索 + 封面
    w._set_nav(0)
    pump(1.5)
    grab("app_search.png")
    # 歌词页
    w.play_row(0)
    pump(9)
    w._set_nav(2)
    pump(6)
    grab("app_lyrics.png")
    # 曲库页
    w._set_nav(1)
    pump(1.2)
    grab("app_library.png")
    # 队列页（触发一次无损下载，抓"下载中"和"完成"两态）
    w.cmb_quality.setCurrentIndex(0)
    big = None
    for s in w.songs:
        try:
            if int(s.get("duration") or 0) > 250:
                big = s
                break
        except Exception:
            pass
    w.download_song(big or w.songs[0])
    w._set_nav(3)
    app.processEvents()
    pump(0.9)
    grab("app_queue_progress.png")     # 下载中（进度条）
    pump(45)
    grab("app_queue.png")              # 完成后
    # 设置页
    w._set_nav(4)
    pump(1.0)
    grab("app_settings.png")
    if w.player:
        w.player.stop()
    app.quit()


QTimer.singleShot(300, run)
app.exec()
print("完成 →", OUT)
