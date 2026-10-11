#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""音乐盒 Studio 功能联调：搜索 / 流媒体试听 / 下载 / 歌词 / 队列。"""
import os
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from PySide6.QtCore import QTimer                       # noqa: E402
from PySide6.QtWidgets import QApplication              # noqa: E402
import kuwo_app as A                                    # noqa: E402

app = QApplication([])
app.setStyleSheet(A.QSS)
w = A.Studio()
w.resize(1340, 860)
state = {"stage": 0, "ok": [], "fail": []}


def pump(sec):
    t0 = time.time()
    while time.time() - t0 < sec:
        app.processEvents()
        time.sleep(0.03)


def log(msg):
    print("· " + msg)


def stage1():
    log("阶段1：搜索「富士山下 陈奕迅」")
    w.ed_search.setText("富士山下 陈奕迅")
    w.do_search()
    pump(12)
    if w.tbl.rowCount() > 0:
        state["ok"].append("搜索 %d 条" % w.tbl.rowCount())
        log("  表格 %d 行；首行 = %s / %s"
            % (w.tbl.rowCount(), w.tbl.item(0, 0).text(), w.tbl.item(0, 1).text()))
        log("  封面 icon: %s" % ("有" if not w.tbl.item(0, 0).icon().isNull() else "无"))
    else:
        state["fail"].append("搜索无结果")
        log("  ✗ 搜索无结果")
    QTimer.singleShot(50, stage2)


def stage2():
    log("阶段2：流媒体试听（不下载直接播线上地址）")
    w.play_row(0)
    pump(10)
    p = w.player
    if p and p.playbackState().name != "StoppedState":
        state["ok"].append("试听成功")
        log("  状态=%s 时长=%dms 位置=%dms 曲目=%s"
            % (p.playbackState().name, p.duration(), p.position(), w.lbl_title.text()))
    else:
        state["fail"].append("试听未进入播放")
        log("  ✗ 试听未播放：state=%s err=%s" % (p.playbackState().name if p else None,
                                                p.errorString() if p else None))
    QTimer.singleShot(50, stage3)


def stage3():
    log("阶段3：下载 128k MP3（走下载队列页）")
    w.cmb_quality.setCurrentIndex(2)
    rid = w.songs[0]["rid"]
    target = None
    for p in w.local:
        if "[%s]" % rid in os.path.basename(p):
            target = p
            break
    old = os.path.getmtime(target) if target else 0
    w.download_song(w.songs[0])
    ok = False
    for _ in range(90):
        pump(1)
        for p in w.local:
            if "[%s]" % rid in os.path.basename(p) and os.path.getmtime(p) > old:
                ok = True
                break
        if ok:
            break
    if ok:
        state["ok"].append("下载成功")
        log("  文件已更新：%s" % os.path.basename(target or p))
    else:
        state["fail"].append("下载未完成")
        log("  ✗ 下载未完成（队列行 %d）" % w.tbl3.rowCount())
    QTimer.singleShot(50, stage4)


def stage4():
    log("阶段4：歌词")
    w.engine.lyric(w.songs[0])          # 传完整歌曲对象（歌名/歌手/时长都会带上）
    pump(8)
    n = len(w.lyric_data)
    if n:
        state["ok"].append("歌词 %d 行" % n)
        log("  歌词 %d 行，首行：%s" % (n, w.lyric_data[0][1][:40]))
    else:
        log("  该曲无歌词（不视为失败）")
    QTimer.singleShot(50, stage5)


def stage5():
    log("阶段5：本地曲库 / 队列导航 / 音量 / 进度")
    w.reload_local()
    log("  本地曲库 %d 首" % len(w.local))
    w.enqueue(w.songs[1] if len(w.songs) > 1 else w.songs[0])
    log("  队列长度 %d" % len(w.queue))
    w.sld_vol.setValue(50)
    pump(0.3)
    log("  音量=%d  播放模式=%s" % (w.sld_vol.value(), w.mode))
    w.cycle_mode()
    log("  切换模式 → %s" % w.mode)
    if w.player:
        w.player.stop()
    print("\n=== 结果：成功 %d 项，失败 %d 项 ===" % (len(state["ok"]), len(state["fail"])))
    for s in state["ok"]:
        print("   ✓ " + s)
    for s in state["fail"]:
        print("   ✗ " + s)
    app.quit()


QTimer.singleShot(200, stage1)
app.exec()
print("联调结束")
