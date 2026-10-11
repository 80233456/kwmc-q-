#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音乐盒 Studio · 酷我音源桌面播放器（PySide6 / Qt 6）
=================================================================
界面全部使用 ui_kit 的矢量图标与自绘控件：无 emoji、无字体依赖；
歌词页为自绘动画组件（平滑滚动 + 卡拉OK渐变 + 点击跳转）。

结构与引擎沿用既有实现（Engine/Worker 线程模型），UI 层重写。
"""
import json
import math
import os
import re
import sys
import time
import urllib.request

from PySide6.QtCore import (QEasingCurve, QObject, QPoint, QPropertyAnimation, QRectF, QSize,
                            Qt, QThread, QTimer, QUrl, Signal, Slot)
from PySide6.QtGui import (QColor, QFont, QFontMetrics, QIcon, QKeySequence, QPainter,
                           QPixmap, QShortcut)
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFileDialog, QFrame,
                               QGraphicsOpacityEffect, QHBoxLayout, QHeaderView, QLabel,
                               QLineEdit, QMenu, QMessageBox, QProgressBar, QPushButton, QSlider,
                               QStackedWidget, QStatusBar, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kuwo_pc_download as K          # noqa: E402
import ui_kit as UK                   # noqa: E402

try:
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
    HAVE_AUDIO = True
except Exception:
    HAVE_AUDIO = False

APP_NAME = "音乐盒 Studio"


def user_dir():
    """用户级持久目录：单文件版(onefile)解压目录每次运行都会重建，
    配置/缓存必须放到用户目录，否则每次退出就丢。"""
    if getattr(sys, "frozen", False):
        d = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"),
                         "MusicBoxStudio")
    else:
        d = os.path.join(HERE, "work")
    os.makedirs(d, exist_ok=True)
    return d


CFG_FILE = os.path.join(user_dir(), "studio_settings.json")
QUALITIES = [("无损 FLAC", "flac", "2000kflac"),
             ("320k MP3", "mp3", "320kmp3"),
             ("128k MP3", "mp3", "128kmp3")]
T = UK.THEME

# --------------------------------------------------------------------------- #
#  样式（补充 ui_kit 之外的部分）
# --------------------------------------------------------------------------- #
QSS = f"""
* {{ font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif; }}
QWidget {{ background: {T['bg']}; color: {T['text']}; font-size: 13px; }}
QLabel#h1 {{ font-size: 20px; font-weight: 700; color: #ffffff; }}
QLabel#h2 {{ font-size: 15px; font-weight: 600; color: #dfe2ea; }}
QLabel#muted {{ color: {T['muted']}; font-size: 12px; }}
QLabel#time {{ color: {T['muted']}; font-family: Consolas, monospace; font-size: 12px; }}
QFrame#card {{ background: {T['card']}; border-radius: 14px; }}
QFrame#sidebar {{ background: {T['panel']}; border-right: 1px solid {T['line']}; }}
QFrame#player {{ background: {T['panel']}; border-top: 1px solid {T['line']}; }}
QLineEdit, QComboBox {{ background: #1b1f28; border: 1px solid #2a3040; border-radius: 10px;
      padding: 8px 12px; selection-background-color: {T['accent']}; }}
QLineEdit:focus, QComboBox:focus {{ border: 1px solid {T['accent']}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{ background: #1b1f28; border: 1px solid #2a3040;
      selection-background-color: {T['accent']}; outline: none; padding: 4px; }}
QPushButton {{ background: #232838; border: 1px solid #2f3648; border-radius: 10px;
      padding: 8px 16px; color: {T['text']}; }}
QPushButton:hover {{ background: #2b3145; }}
QPushButton:pressed {{ background: #1d2230; }}
QPushButton#primary {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
      stop:0 {T['accent']}, stop:1 {T['accent2']}); border: none; font-weight: 700; color: #fff; }}
QPushButton#primary:hover {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
      stop:0 #7d6ef0, stop:1 #14c9a2); }}
QTableWidget {{ background: {T['panel']}; border: none; gridline-color: {T['line']};
      selection-background-color: #22283a; selection-color: #ffffff; outline: none; }}
QHeaderView::section {{ background: {T['panel']}; color: {T['muted']}; border: none;
      border-bottom: 1px solid {T['line']}; padding: 9px 6px; font-weight: 600; }}
QTableWidget::item {{ padding: 6px; border-bottom: 1px solid #171b23; }}
QTableWidget::item:hover {{ background: #1b2030; }}
QTableWidget::item:selected {{ background: #22283a; }}
QSlider::groove:horizontal {{ height: 5px; background: #262c3a; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
      stop:0 {T['accent']}, stop:1 {T['accent2']}); border-radius: 2px; }}
QSlider::handle:horizontal {{ width: 12px; height: 12px; margin: -4px 0; border-radius: 6px;
      background: #ffffff; }}
QSlider::handle:horizontal:hover {{ width: 16px; height: 16px; margin: -6px 0; border-radius: 8px;
      background: #ffffff; }}
QProgressBar {{ background: #1b1f28; border: none; border-radius: 6px; height: 8px; }}
QProgressBar::chunk {{ border-radius: 6px; background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
      stop:0 {T['accent']}, stop:1 {T['accent2']}); }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #2c3346; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #3a4359; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QStatusBar {{ background: {T['panel']}; color: {T['muted']}; }}
QCheckBox {{ color: {T['muted']}; }}
QCheckBox::indicator {{ width: 15px; height: 15px; border-radius: 4px; background: #1b1f28;
      border: 1px solid #2a3040; }}
QCheckBox::indicator:checked {{ background: {T['accent']}; border: 1px solid {T['accent']}; }}
QToolTip {{ background: #1b1f28; color: {T['text']}; border: 1px solid #2a3040;
      border-radius: 6px; padding: 5px 8px; }}
"""


# --------------------------------------------------------------------------- #
#  后台任务
# --------------------------------------------------------------------------- #
class Worker(QThread):
    done = Signal(object)
    fail = Signal(str)

    def __init__(self, fn, *args, **kw):
        super().__init__()
        self.fn, self.args, self.kw = fn, args, kw

    def run(self):
        try:
            self.done.emit(self.fn(*self.args, **self.kw))
        except Exception as e:
            self.fail.emit(str(e))


class Engine(QObject):
    """网络操作统一走线程 + 信号（不阻塞 UI）。"""
    searched = Signal(list)
    sizeGot = Signal(str, int, str)
    downloaded = Signal(dict)
    lyricGot = Signal(str, object)
    progress = Signal(str, int)
    failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tasks = []

    def _run(self, fn, on_done, *args, **kw):
        w = Worker(fn, *args, **kw)
        w.done.connect(lambda r, cb=on_done: cb(r))
        w.fail.connect(lambda e: self.failed.emit(e))
        w.finished.connect(lambda: self.tasks.remove(w) if w in self.tasks else None)
        self.tasks.append(w)
        w.start()
        return w

    def search(self, kw):
        self._run(K.search, lambda r: self.searched.emit(r), kw)

    def probe(self, song, fmt, br):
        def job():
            u, f, _b = K.resolve_url(song["rid"], fmt, br)
            return (song["rid"], (K.remote_size(u) if u else 0), f or "")
        self._run(job, lambda r: self.sizeGot.emit(*r))

    def download(self, song, fmt, br, save_lyric=True):
        rid = song["rid"]

        def stream(url, path):
            """分块下载并回报真实进度（0-100）。"""
            req = urllib.request.Request(url, headers={"User-Agent": K.UA_OK})
            tmp = path + ".part"
            with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "wb") as f:
                total = int(r.headers.get("Content-Length") or 0)
                got, last = 0, -1
                while True:
                    chunk = r.read(262144)
                    if not chunk:
                        break
                    f.write(chunk)
                    got += len(chunk)
                    if total:
                        pct = int(got * 100 / total)
                        if pct != last:
                            last = pct
                            self.progress.emit(rid, pct)
            os.replace(tmp, path)
            return got

        def job():
            u, f, _b = K.resolve_url(song["rid"], fmt, br)
            if not u:
                u, f, _b = K.resolve_url(song["rid"], "mp3", "128kmp3")
            if not u:
                raise RuntimeError("拿不到可用地址")
            ext = f or fmt
            os.makedirs(K.OUTDIR, exist_ok=True)
            path = os.path.join(K.OUTDIR, "%s - %s [%s].%s"
                                % (K.safe_name(song["name"]), K.safe_name(song["artist"]),
                                   song["rid"], ext))
            n = stream(u, path)
            if ext == "flac":
                tg = K.flac_tags(path)
                if tg.get("title"):
                    np_ = os.path.join(K.OUTDIR, "%s - %s [%s].flac"
                                       % (K.safe_name(tg["title"]),
                                          K.safe_name(tg.get("artist") or ""), song["rid"]))
                    if os.path.abspath(np_) != os.path.abspath(path):
                        os.replace(path, np_)
                        path = np_
            if save_lyric:
                lrc = K.fetch_lyric(song["rid"], song.get("name", ""),
                                    song.get("artist", ""), song.get("duration") or 0)
                if lrc:
                    with open(path.rsplit(".", 1)[0] + ".lrc", "w", encoding="utf-8") as fh:
                        fh.write(lrc)
            self.progress.emit(rid, 100)
            return {"song": song, "path": path, "size": n, "format": ext}
        self._run(job, lambda r: self.downloaded.emit(r))

    def lyric(self, song):
        if isinstance(song, str):
            song = {"rid": song}
        rid = song.get("rid", "")

        def job():
            return (rid, K.fetch_lyric(rid, song.get("name", ""), song.get("artist", ""),
                                       song.get("duration") or 0) or "")
        self._run(job, lambda r: self.lyricGot.emit(*r))


def cover_url(song):
    short = song.get("pic_short") or ""
    parts = short.split("/")
    if len(parts) >= 4:
        return "https://img1.kuwo.cn/star/albumcover/500/" + "/".join(parts[1:])
    return ""


def lrc_lines(txt):
    out = []
    for line in (txt or "").splitlines():
        tags = re.findall(r"\[(\d+):(\d+(?:\.\d+)?)\]", line)
        text = re.sub(r"\[[^\]]*\]", "", line).strip()
        for mm, ss in tags:
            out.append((int(mm) * 60000 + int(float(ss) * 1000), text))
    out.sort(key=lambda x: x[0])
    return out


# --------------------------------------------------------------------------- #
#  侧栏导航项（自绘图标 + 动画选中指示条）
# --------------------------------------------------------------------------- #
class NavItem(QWidget):
    clicked = Signal(int)

    def __init__(self, icon_name, text, index, parent=None):
        super().__init__(parent)
        self.icon_name, self.text, self.index = icon_name, text, index
        self.selected = False
        self.hover = False
        self._hl = 0.0            # 高亮动画 0→1
        self.setFixedHeight(44)
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)
        self._t = QTimer(self)
        self._t.timeout.connect(self._tick)
        self._t.start(16)

    def set_selected(self, on):
        self.selected = on
        self.update()

    def _tick(self):
        target = 1.0 if self.selected else (0.42 if self.hover else 0.0)
        if abs(self._hl - target) > 0.01:
            self._hl += (target - self._hl) * 0.25
            self.update()

    def enterEvent(self, _e):
        self.hover = True

    def leaveEvent(self, _e):
        self.hover = False

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit(self.index)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = QRectF(self.rect()).adjusted(6, 3, -6, -3)
        if self._hl > 0.01:
            if self.selected:
                grad = UK.accent_gradient(r)
                p.setPen(Qt.NoPen)
                p.setBrush(grad)
                p.setOpacity(0.16 + 0.14 * self._hl)
                p.drawRoundedRect(r, 10, 10)
                p.setOpacity(1.0)
            else:
                c = QColor(T["hover"])
                c.setAlphaF(self._hl)
                p.setPen(Qt.NoPen)
                p.setBrush(c)
                p.drawRoundedRect(r, 10, 10)
        if self.selected:      # 左侧指示条（随选中动画显现）
            bar = QRectF(r.left() + 1, r.center().y() - 9 * self._hl, 3, 18 * self._hl)
            p.setPen(Qt.NoPen)
            p.setBrush(UK.accent_gradient(bar))
            p.drawRoundedRect(bar, 1.5, 1.5)
        col = "#ffffff" if self.selected else (T["text"] if self.hover else T["muted"])
        pm = UK.icon_pixmap(self.icon_name, 18, col, self.devicePixelRatioF())
        p.drawPixmap(int(r.left() + 14), int(r.center().y() - 9), pm)
        f = QFont("Microsoft YaHei UI", 10)
        f.setBold(self.selected)
        p.setFont(f)
        p.setPen(QColor(col))
        p.drawText(QRectF(r.left() + 44, r.top(), r.width() - 48, r.height()),
                   Qt.AlignVCenter | Qt.AlignLeft, self.text)
        p.end()


# --------------------------------------------------------------------------- #
#  Toast（右下角浮出提示）
# --------------------------------------------------------------------------- #
class Toast(QLabel):
    def __init__(self, parent):
        super().__init__(parent)
        self.setStyleSheet(
            "background:#1d2230;color:#e6e8ee;border:1px solid #2f3648;"
            "border-radius:10px;padding:9px 16px;font-size:12px;")
        self.setVisible(False)
        self._eff = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._eff)
        self._anim = QPropertyAnimation(self._eff, b"opacity", self)
        self._anim.setDuration(220)
        self._fading_out = False
        self._anim.finished.connect(self._on_anim_done)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._fade_out)

    def show_msg(self, text, ms=2600):
        self.setText(text)
        self.adjustSize()
        x = self.parent().width() - self.width() - 26
        y = self.parent().height() - self.height() - 120
        self.move(max(10, x), max(10, y))
        self.setVisible(True)
        self.raise_()
        self._eff.setOpacity(0.0)
        self._fading_out = False
        self._anim.stop()
        self._anim.setStartValue(self._eff.opacity())
        self._anim.setEndValue(1.0)
        self._anim.start()
        self._timer.start(ms)

    def _on_anim_done(self):
        if self._fading_out:
            self.hide()

    def _fade_out(self):
        self._fading_out = True
        self._anim.stop()
        self._anim.setStartValue(self._eff.opacity())
        self._anim.setEndValue(0.0)
        self._anim.start()


# --------------------------------------------------------------------------- #
#  主窗口
# --------------------------------------------------------------------------- #
class Studio(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1360, 880)
        self.setMinimumSize(1100, 720)
        self.cfg = self.load_cfg()
        self.engine = Engine(self)
        self.songs, self.sizes, self.local, self.queue = [], {}, [], []
        self.q_index = -1
        self.cur_song = None
        self.lyric_data = []
        self.dl_rows = {}
        self.covers = {}
        self.mode = "顺序"
        self._build_ui()
        self._wire()
        self.reload_local()

    # ---------------- 配置 ----------------
    def load_cfg(self):
        d = {"quality": 0, "lyric": True, "volume": 70, "query": "", "dir": K.OUTDIR}
        try:
            with open(CFG_FILE, encoding="utf-8") as f:
                d.update(json.load(f))
        except Exception:
            pass
        return d

    def save_cfg(self):
        try:
            os.makedirs(os.path.dirname(CFG_FILE), exist_ok=True)
            self.cfg.update({"quality": self.cmb_quality.currentIndex(),
                             "lyric": self.chk_lyric.isChecked(),
                             "volume": self.sld_vol.value(),
                             "query": self.ed_search.text()})
            with open(CFG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.cfg, f, ensure_ascii=False, indent=1)
        except Exception:
            pass

    # ---------------- 界面 ----------------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        root.addLayout(body, 1)

        # -------- 侧栏 --------
        side = QFrame()
        side.setObjectName("sidebar")
        side.setFixedWidth(198)
        sv = QVBoxLayout(side)
        sv.setContentsMargins(12, 16, 12, 12)
        sv.setSpacing(6)
        logo_row = QHBoxLayout()
        logo_ic = QLabel()
        logo_ic.setPixmap(UK.icon_pixmap("note", 22, T["accent"], self.devicePixelRatioF()))
        logo_row.addWidget(logo_ic)
        ttl = QLabel("音乐盒 Studio")
        ttl.setObjectName("h1")
        logo_row.addWidget(ttl)
        logo_row.addStretch(1)
        sv.addLayout(logo_row)
        sub = QLabel("酷我音源 · 试听 · 无损下载")
        sub.setObjectName("muted")
        sv.addWidget(sub)
        sv.addSpacing(10)
        self.nav_items = []
        for i, (ic, tx) in enumerate((("search", "搜索"), ("library", "本地曲库"),
                                      ("lyric", "歌词"), ("queue", "下载队列"),
                                      ("settings", "设置"))):
            it = NavItem(ic, tx, i)
            it.clicked.connect(self._on_nav)
            sv.addWidget(it)
            self.nav_items.append(it)
        sv.addStretch(1)
        shortcut = QLabel("空格 播放/暂停\n← → 快退快进\nCtrl+F 搜索")
        shortcut.setObjectName("muted")
        sv.addWidget(shortcut)
        body.addWidget(side)

        # -------- 主区 --------
        main = QVBoxLayout()
        main.setContentsMargins(18, 16, 18, 8)
        main.setSpacing(12)
        body.addLayout(main, 1)

        top = QHBoxLayout()
        top.setSpacing(10)
        self.ed_search = QLineEdit(self.cfg.get("query", ""))
        self.ed_search.setPlaceholderText("搜索歌曲 / 歌手 / 专辑，例如：富士山下 陈奕迅")
        self.ed_search.setClearButtonEnabled(True)
        self.ed_search.setMinimumHeight(38)
        top.addWidget(self.ed_search, 1)
        self.cmb_quality = QComboBox()
        self.cmb_quality.addItems([q[0] for q in QUALITIES])
        self.cmb_quality.setCurrentIndex(int(self.cfg.get("quality", 0)))
        self.cmb_quality.setMinimumHeight(38)
        top.addWidget(self.cmb_quality)
        self.chk_lyric = QCheckBox("下载歌词")
        self.chk_lyric.setChecked(bool(self.cfg.get("lyric", True)))
        top.addWidget(self.chk_lyric)
        self.btn_search = QPushButton("  搜索  ")
        self.btn_search.setObjectName("primary")
        self.btn_search.setMinimumHeight(38)
        top.addWidget(self.btn_search)
        main.addLayout(top)

        self.stack = QStackedWidget()
        main.addWidget(self.stack, 1)

        # --- 搜索页 ---
        page1 = QWidget()
        p1 = QVBoxLayout(page1)
        p1.setContentsMargins(0, 0, 0, 0)
        p1.setSpacing(0)
        self.tbl = QTableWidget(0, 6)
        self.tbl.setHorizontalHeaderLabels(["歌曲", "歌手", "专辑", "时长", "音质", "操作"])
        self.tbl.verticalHeader().setVisible(False)
        self.tbl.setShowGrid(False)
        self.tbl.setIconSize(QSize(44, 44))
        hh = self.tbl.horizontalHeader()
        for i, w in enumerate((320, 150, 220, 70, 168, 110)):
            hh.setSectionResizeMode(i, QHeaderView.Fixed)
            self.tbl.setColumnWidth(i, w)
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        self.tbl.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl.setContextMenuPolicy(Qt.CustomContextMenu)
        self.empty1 = UK.EmptyState("search", "输入关键词开始搜索",
                                   "试试：富士山下 陈奕迅 / 周杰伦 晴天 / 演员 薛之谦")
        self.stack_holder1 = QStackedWidget()
        self.stack_holder1.addWidget(self.empty1)
        self.stack_holder1.addWidget(self.tbl)
        p1.addWidget(self.stack_holder1)
        self.stack.addWidget(page1)

        # --- 本地曲库页 ---
        page2 = QWidget()
        p2 = QVBoxLayout(page2)
        p2.setContentsMargins(0, 0, 0, 0)
        p2.setSpacing(8)
        bar2 = QHBoxLayout()
        self.lbl_dir = QLabel()
        self.lbl_dir.setObjectName("muted")
        bar2.addWidget(self.lbl_dir, 1)
        self.btn_open = UK.IconButton("folder", tooltip="打开下载目录")
        self.btn_refresh = UK.IconButton("refresh", tooltip="刷新本地曲库")
        bar2.addWidget(self.btn_open)
        bar2.addWidget(self.btn_refresh)
        p2.addLayout(bar2)
        self.tbl2 = QTableWidget(0, 4)
        self.tbl2.setHorizontalHeaderLabels(["#", "文件", "歌手", "大小"])
        self.tbl2.verticalHeader().setVisible(False)
        self.tbl2.setShowGrid(False)
        self.tbl2.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tbl2.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl2.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl2.setContextMenuPolicy(Qt.CustomContextMenu)
        self.empty2 = UK.EmptyState("library", "本地还没有歌曲", "搜索后右键「下载」，或点击歌曲自动缓存")
        self.stack_holder2 = QStackedWidget()
        self.stack_holder2.addWidget(self.empty2)
        self.stack_holder2.addWidget(self.tbl2)
        p2.addWidget(self.stack_holder2)
        self.stack.addWidget(page2)

        # --- 歌词页 ---
        page3 = QWidget()
        p3 = QVBoxLayout(page3)
        p3.setContentsMargins(0, 0, 0, 0)
        p3.setSpacing(8)
        head = QHBoxLayout()
        self.lbl_lyric_song = QLabel("未播放")
        self.lbl_lyric_song.setObjectName("h2")
        head.addWidget(self.lbl_lyric_song)
        head.addStretch(1)
        self.lbl_lyric_hint = QLabel("点击任意一行可跳转播放位置")
        self.lbl_lyric_hint.setObjectName("muted")
        head.addWidget(self.lbl_lyric_hint)
        p3.addLayout(head)
        card = QFrame()
        card.setObjectName("card")
        cv = QVBoxLayout(card)
        cv.setContentsMargins(6, 6, 6, 6)
        self.lyrics_view = UK.LyricsView(card)
        cv.addWidget(self.lyrics_view)
        p3.addWidget(card, 1)
        self.stack.addWidget(page3)

        # --- 下载队列页 ---
        page4 = QWidget()
        p4 = QVBoxLayout(page4)
        p4.setContentsMargins(0, 0, 0, 0)
        self.tbl3 = QTableWidget(0, 5)
        self.tbl3.setHorizontalHeaderLabels(["歌曲", "歌手", "音质", "状态", "进度"])
        self.tbl3.verticalHeader().setVisible(False)
        self.tbl3.setShowGrid(False)
        self.tbl3.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tbl3.setColumnWidth(1, 120)
        self.tbl3.setColumnWidth(2, 110)
        self.tbl3.setColumnWidth(3, 150)
        self.tbl3.setColumnWidth(4, 190)
        self.tbl3.setEditTriggers(QTableWidget.NoEditTriggers)
        self.empty4 = UK.EmptyState("download", "下载队列为空", "在搜索结果上右键「下载（当前音质）」")
        self.stack_holder4 = QStackedWidget()
        self.stack_holder4.addWidget(self.empty4)
        self.stack_holder4.addWidget(self.tbl3)
        p4.addWidget(self.stack_holder4)
        self.stack.addWidget(page4)

        # --- 设置页 ---
        page5 = QWidget()
        p5 = QVBoxLayout(page5)
        p5.setContentsMargins(0, 0, 0, 0)
        p5.setSpacing(12)
        card2 = QFrame()
        card2.setObjectName("card")
        cv2 = QVBoxLayout(card2)
        cv2.setContentsMargins(20, 18, 20, 18)
        cv2.setSpacing(10)
        t2 = QLabel("下载目录")
        t2.setObjectName("h2")
        cv2.addWidget(t2)
        row2 = QHBoxLayout()
        self.ed_dir = QLineEdit(self.cfg.get("dir") or K.OUTDIR)
        row2.addWidget(self.ed_dir, 1)
        b = QPushButton("选择…")
        b.clicked.connect(self.pick_dir)
        row2.addWidget(b)
        cv2.addLayout(row2)
        note = QLabel("试听不需要下载：双击歌曲即播放线上地址。\n"
                      "下载会按内嵌标签规范命名（歌名 - 歌手 [rid].扩展名），并可选保存歌词。")
        note.setObjectName("muted")
        note.setWordWrap(True)
        cv2.addWidget(note)
        p5.addWidget(card2)

        # 播放设置
        card3 = QFrame()
        card3.setObjectName("card")
        cv3 = QVBoxLayout(card3)
        cv3.setContentsMargins(20, 18, 20, 18)
        cv3.setSpacing(10)
        t3 = QLabel("播放")
        t3.setObjectName("h2")
        cv3.addWidget(t3)
        rowv = QHBoxLayout()
        rowv.addWidget(QLabel("启动音量"))
        self.sld_defvol = QSlider(Qt.Horizontal)
        self.sld_defvol.setRange(0, 100)
        self.sld_defvol.setValue(int(self.cfg.get("volume", 70)))
        self.sld_defvol.setFixedWidth(220)
        lbl_defvol = QLabel("%d%%" % self.sld_defvol.value())
        lbl_defvol.setObjectName("muted")
        self.sld_defvol.valueChanged.connect(
            lambda v: (lbl_defvol.setText("%d%%" % v), self.sld_vol.setValue(v)))
        rowv.addWidget(self.sld_defvol)
        rowv.addWidget(lbl_defvol)
        rowv.addStretch(1)
        cv3.addLayout(rowv)
        p5.addWidget(card3)

        # 缓存与关于
        card4 = QFrame()
        card4.setObjectName("card")
        cv4 = QVBoxLayout(card4)
        cv4.setContentsMargins(20, 18, 20, 18)
        cv4.setSpacing(10)
        t4 = QLabel("缓存与关于")
        t4.setObjectName("h2")
        cv4.addWidget(t4)
        self.lbl_cache = QLabel()
        self.lbl_cache.setObjectName("muted")
        cv4.addWidget(self.lbl_cache)
        rowc = QHBoxLayout()
        b_cl = QPushButton("清空歌词缓存")
        b_cl.clicked.connect(self.clear_cache)
        b_cv = QPushButton("清空封面缓存")
        b_cv.clicked.connect(self.clear_covers)
        b_dir = QPushButton("打开下载目录")
        b_dir.clicked.connect(self.open_dir)
        for b3 in (b_cl, b_cv, b_dir):
            rowc.addWidget(b3)
        rowc.addStretch(1)
        cv4.addLayout(rowc)
        about = QLabel("音乐盒 Studio · 音源：酷我（搜索/试听/无损下载）\n"
                       "界面：PySide6 / Qt 6 　引擎：自研 q 参数加密（kuwo_q.py）\n"
                       "快捷键：空格 播放/暂停　← → 快退快进　Ctrl+F 搜索")
        about.setObjectName("muted")
        cv4.addWidget(about)
        p5.addWidget(card4)
        p5.addStretch(1)
        self.stack.addWidget(page5)

        # -------- 播放条 --------
        pl = QFrame()
        pl.setObjectName("player")
        pl.setFixedHeight(104)
        pv = QHBoxLayout(pl)
        pv.setContentsMargins(18, 12, 18, 12)
        pv.setSpacing(14)
        self.lbl_cover = QLabel()
        self.lbl_cover.setFixedSize(72, 72)
        self.lbl_cover.setAlignment(Qt.AlignCenter)
        self._set_cover_pixmap(None)
        pv.addWidget(self.lbl_cover)
        info = QVBoxLayout()
        info.setSpacing(3)
        self.lbl_title = QLabel("未播放")
        self.lbl_title.setObjectName("h2")
        self.lbl_artist = QLabel("—")
        self.lbl_artist.setObjectName("muted")
        info.addWidget(self.lbl_title)
        info.addWidget(self.lbl_artist)
        pv.addLayout(info, 0)
        self.eq = UK.EqBars()
        self._set_eq(False)
        pv.addWidget(self.eq)
        pv.addSpacing(6)
        self.btn_prev = UK.IconButton("prev", 40, 20, tooltip="上一首")
        self.btn_play = UK.IconButton("play", 44, 22, tooltip="播放/暂停 (空格)")
        self.btn_stop = UK.IconButton("stop", 36, 16, tooltip="停止")
        self.btn_next = UK.IconButton("next", 40, 20, tooltip="下一首")
        for b2 in (self.btn_prev, self.btn_play, self.btn_stop, self.btn_next):
            pv.addWidget(b2)
        self.btn_mode = UK.IconButton("repeat", 34, 17, tooltip="播放模式：顺序")
        pv.addWidget(self.btn_mode)
        self.lbl_cur = QLabel("00:00")
        self.lbl_cur.setObjectName("time")
        self.sld_seek = QSlider(Qt.Horizontal)
        self.sld_seek.setRange(0, 1000)
        self.lbl_dur = QLabel("00:00")
        self.lbl_dur.setObjectName("time")
        pv.addWidget(self.lbl_cur)
        pv.addWidget(self.sld_seek, 1)
        pv.addWidget(self.lbl_dur)
        self.btn_lyric = UK.IconButton("lyric", 36, 18, tooltip="歌词页")
        pv.addWidget(self.btn_lyric)
        self.btn_vol = UK.IconButton("volume", 34, 17, tooltip="静音/取消静音")
        pv.addWidget(self.btn_vol)
        self.sld_vol = QSlider(Qt.Horizontal)
        self.sld_vol.setRange(0, 100)
        self.sld_vol.setValue(int(self.cfg.get("volume", 70)))
        self.sld_vol.setFixedWidth(110)
        pv.addWidget(self.sld_vol)
        root.addWidget(pl)

        self.status = QStatusBar()
        root.addWidget(self.status)

        self.toast = Toast(self)
        self.spinner = UK.Spinner(20)
        self.spinner.hide()

        # 播放器
        if HAVE_AUDIO:
            self.player = QMediaPlayer(self)
            self.audio = QAudioOutput(self)
            self.player.setAudioOutput(self.audio)
            self.audio.setVolume(self.sld_vol.value() / 100.0)
        else:
            self.player = self.audio = None
        self._set_nav(0)

    # ---------------- 封面/占位 ----------------
    def _set_eq(self, on):
        """播放律动指示：只在播放时显示，否则隐藏（不占位）。"""
        self.eq.set_playing(on)
        self.eq.setVisible(bool(on))

    def _set_cover_pixmap(self, pm, size=72):
        if pm is None:
            self.lbl_cover.setStyleSheet(
                "background:%s;border-radius:12px;" % T["card"])
            self.lbl_cover.setPixmap(UK.icon_pixmap("note", 30, T["dim"],
                                                    self.devicePixelRatioF()))
        else:
            self.lbl_cover.setStyleSheet(
                "background:%s;border-radius:12px;" % T["card"])
            self.lbl_cover.setPixmap(pm.scaled(size, size, Qt.KeepAspectRatio,
                                               Qt.SmoothTransformation))

    # ---------------- 信号 ----------------
    def _wire(self):
        self.btn_search.clicked.connect(self.do_search)
        self.ed_search.returnPressed.connect(self.do_search)
        self.tbl.cellDoubleClicked.connect(lambda r, c: self.play_row(r))
        self.tbl.customContextMenuRequested.connect(self.tbl_menu)
        self.tbl2.cellDoubleClicked.connect(lambda r, c: self.play_local(r))
        self.tbl2.customContextMenuRequested.connect(self.tbl2_menu)
        self.btn_play.clicked.connect(self.toggle_play)
        self.btn_prev.clicked.connect(lambda: self.step(-1))
        self.btn_next.clicked.connect(lambda: self.step(1))
        self.btn_stop.clicked.connect(self.stop)
        self.btn_mode.clicked.connect(self.cycle_mode)
        self.btn_lyric.clicked.connect(lambda: self.go_page(2))
        self.btn_vol.clicked.connect(self.toggle_mute)
        self.btn_open.clicked.connect(self.open_dir)
        self.btn_refresh.clicked.connect(self.reload_local)
        self.sld_vol.valueChanged.connect(self.on_vol)
        self.sld_seek.sliderReleased.connect(self.on_seek)
        self.lyrics_view.seekRequested.connect(self.on_lyric_click)
        QShortcut(QKeySequence("Space"), self, activated=self.toggle_play)
        QShortcut(QKeySequence("Right"), self, activated=lambda: self.nudge(5))
        QShortcut(QKeySequence("Left"), self, activated=lambda: self.nudge(-5))
        QShortcut(QKeySequence("Ctrl+F"), self, activated=self.ed_search.setFocus)
        self.engine.searched.connect(self.on_searched)
        self.engine.sizeGot.connect(self.on_size)
        self.engine.progress.connect(self.on_progress)
        self.engine.downloaded.connect(self.on_downloaded)
        self.engine.lyricGot.connect(self.on_lyric)
        self.engine.failed.connect(lambda e: self.toast.show_msg("出错：" + e[:100]))
        if self.player:
            self.player.positionChanged.connect(self.on_pos)
            self.player.durationChanged.connect(self.on_dur)
            self.player.mediaStatusChanged.connect(self.on_media_status)
            self.player.errorOccurred.connect(
                lambda e, s: self.toast.show_msg("播放错误：%s" % s))
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick_lyric)
        self.timer.start(400)

    def _on_nav(self, idx):
        self._set_nav(idx)

    def _set_nav(self, idx):
        for i, it in enumerate(self.nav_items):
            it.set_selected(i == idx)
        self.stack.setCurrentIndex(idx)

    def go_page(self, idx):
        self._set_nav(idx)

    # ---------------- 搜索 ----------------
    def do_search(self):
        kw = self.ed_search.text().strip()
        if not kw:
            self.toast.show_msg("请输入关键词")
            return
        self.status.showMessage("搜索中…")
        self.engine.search(kw)

    @Slot(list)
    def on_searched(self, res):
        self.songs, self.sizes = res, {}
        self.tbl.setRowCount(0)
        for s in res:
            r = self.tbl.rowCount()
            self.tbl.insertRow(r)
            it0 = QTableWidgetItem(s["name"])
            it0.setIcon(QIcon(UK.icon_pixmap("note", 40, T["dim"],
                                             self.devicePixelRatioF())))
            self.tbl.setItem(r, 0, it0)
            self.tbl.setItem(r, 1, QTableWidgetItem(s["artist"]))
            self.tbl.setItem(r, 2, QTableWidgetItem(s.get("album", "")))
            dur = s.get("duration")
            self.tbl.setItem(r, 3, QTableWidgetItem(
                "%d:%02d" % (int(dur) // 60, int(dur) % 60) if str(dur).isdigit() else "-"))
            q = s.get("minsize") or ""
            if s.get("pay"):
                q = ("VIP · " + q) if q else "VIP"
            self.tbl.setItem(r, 4, QTableWidgetItem(q))
            # 操作列：试听 / 下载 图标按钮
            holder = QWidget()
            hl = QHBoxLayout(holder)
            hl.setContentsMargins(2, 2, 2, 2)
            hl.setSpacing(4)
            b_play = UK.IconButton("play", 28, 15, tooltip="试听")
            b_dl = UK.IconButton("download", 28, 15, tooltip="下载（当前音质）")
            b_play.clicked.connect(lambda _=False, row=r: self.play_row(row))
            b_dl.clicked.connect(lambda _=False, row=r: self.download_song(self.songs[row])
                                 if row < len(self.songs) else None)
            hl.addWidget(b_play)
            hl.addWidget(b_dl)
            hl.addStretch(1)
            self.tbl.setCellWidget(r, 5, holder)
            self.tbl.setRowHeight(r, 56)
            self.load_cover(s, r)
        self.stack_holder1.setCurrentIndex(1 if res else 0)
        self.status.showMessage("找到 %d 首" % len(res), 5000)
        if res:
            self.toast.show_msg("找到 %d 首，双击即可试听" % len(res))

    def load_cover(self, song, row):
        url = cover_url(song)
        if not url:
            return
        if url in self.covers:
            self._set_row_icon(row, self.covers[url])
            return

        def job():
            try:
                import urllib.request
                req = urllib.request.Request(url, headers={"User-Agent": K.UA_WEB})
                with urllib.request.urlopen(req, timeout=12) as r:
                    return r.read()
            except Exception:
                return b""
        self.engine._run(job, lambda data: self._cover_ready(url, row, data))

    def _cover_ready(self, url, row, data):
        if not data:
            return
        pm = QPixmap()
        if not pm.loadFromData(data):
            return
        pm = pm.scaled(88, 88, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.covers[url] = pm
        self._set_row_icon(row, pm)
        if self.cur_song and cover_url(self.cur_song) == url:
            self._set_cover_pixmap(pm)

    def _set_row_icon(self, row, pm):
        try:
            if 0 <= row < self.tbl.rowCount():
                item = self.tbl.item(row, 0)
                if item:
                    item.setIcon(QIcon(pm))
        except Exception:
            pass

    # ---------------- 播放 ----------------
    def play_row(self, row):
        if 0 <= row < len(self.songs):
            self.queue = [{"song": s, "url": None, "row": i} for i, s in enumerate(self.songs)]
            self.q_index = row
            self.play_current()

    def play_local(self, row):
        if not (0 <= row < len(self.local)):
            return
        p = self.local[row]
        self.queue = [{"song": {"rid": "", "name": os.path.basename(x), "artist": ""},
                       "url": None, "path": x} for x in self.local]
        self.q_index = row
        self.play_current()

    def play_current(self):
        if not (0 <= self.q_index < len(self.queue)):
            return
        ent = self.queue[self.q_index]
        song = ent["song"]
        if ent.get("path"):
            self._start(QUrl.fromLocalFile(ent["path"]), song)
            return
        if ent.get("url"):
            self._start(QUrl(ent["url"]), song)
            return
        fmt, br = QUALITIES[self.cmb_quality.currentIndex()][1:]
        self.status.showMessage("解析播放地址…")
        self.spinner.show()
        w = Worker(lambda: self._resolve_now(song, fmt, br))
        w.done.connect(lambda res: (self.spinner.hide(), self._on_resolved(ent, song, res)))
        w.fail.connect(lambda e: (self.spinner.hide(), self.toast.show_msg("解析失败：" + e[:80])))
        self.engine.tasks.append(w)
        w.start()

    def _resolve_now(self, song, fmt, br):
        u, f, _b = K.resolve_url(song["rid"], fmt, br)
        if not u:
            u, f, _b = K.resolve_url(song["rid"], "mp3", "128kmp3")
        return {"url": u, "format": f, "size": K.remote_size(u) if u else 0}

    def _on_resolved(self, ent, song, res):
        if not res.get("url"):
            self.toast.show_msg("这首拿不到播放地址（可能受限），试试其它版本")
            return
        ent["url"] = res["url"]
        self._start(QUrl(res["url"]), song)

    def _start(self, qurl, song):
        self.cur_song = song
        self.lbl_title.setText(song.get("name") or "-")
        self.lbl_artist.setText(song.get("artist") or "-")
        self.lbl_lyric_song.setText("%s · %s" % (song.get("name") or "-",
                                                 song.get("artist") or ""))
        if self.player:
            self.player.setSource(qurl)
            self.player.play()
        self.btn_play.set_icon("pause")
        self._set_eq(True)
        self.status.showMessage("正在播放：%s - %s" % (song.get("name"), song.get("artist")), 4000)
        pm = self.covers.get(cover_url(song))
        self._set_cover_pixmap(pm)
        self._mark_playing_row()
        self.engine.lyric(song)

    def toggle_play(self):
        if not self.player:
            return
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
            self.btn_play.set_icon("play")
            self._set_eq(False)
        else:
            if self.player.source().isEmpty() and self.queue:
                self.play_current()
            else:
                self.player.play()
                self.btn_play.set_icon("pause")
                self._set_eq(True)

    def stop(self):
        if self.player:
            self.player.stop()
        self.btn_play.set_icon("play")
        self._set_eq(False)
        self.sld_seek.setValue(0)
        self.lbl_cur.setText("00:00")
        self.lbl_title.setText("已停止")

    def step(self, d):
        if not self.queue:
            return
        if self.mode == "随机":
            import random
            self.q_index = random.randrange(len(self.queue))
        elif self.mode == "单曲":
            if self.player:
                self.player.setPosition(0)
                self.player.play()
            return
        else:
            self.q_index = (self.q_index + d) % len(self.queue)
        self.play_current()

    def cycle_mode(self):
        self.mode = {"顺序": "随机", "随机": "单曲", "单曲": "顺序"}[self.mode]
        icon = {"顺序": "repeat", "随机": "shuffle", "单曲": "repeat1"}[self.mode]
        self.btn_mode.set_icon(icon)
        self.btn_mode.setToolTip("播放模式：%s" % self.mode)
        self.toast.show_msg("播放模式：%s" % self.mode)

    def toggle_mute(self):
        if not self.audio:
            return
        self._muted = not getattr(self, "_muted", False)
        self.audio.setVolume(0.0 if self._muted else self.sld_vol.value() / 100.0)
        self.btn_vol.set_icon("mute" if self._muted else "volume")

    def nudge(self, sec):
        if self.player:
            self.player.setPosition(max(0, self.player.position() + sec * 1000))

    def on_vol(self, v):
        if self.audio and not getattr(self, "_muted", False):
            self.audio.setVolume(v / 100.0)

    def on_seek(self):
        if self.player and self.player.duration():
            self.player.setPosition(int(self.player.duration() * self.sld_seek.value() / 1000))

    def on_lyric_click(self, ms):
        if self.player:
            self.player.setPosition(max(0, int(ms)))
            self.player.play()
            self.btn_play.set_icon("pause")

    def on_pos(self, ms):
        if not self.sld_seek.isSliderDown() and self.player and self.player.duration():
            self.sld_seek.setValue(int(ms * 1000 / self.player.duration()))
        self.lbl_cur.setText("%02d:%02d" % (ms // 60000, (ms // 1000) % 60))
        if self.lyric_data:
            self.lyrics_view.set_position(ms)

    def on_dur(self, ms):
        self.lbl_dur.setText("%02d:%02d" % (ms // 60000, (ms // 1000) % 60))

    def on_media_status(self, st):
        if st == QMediaPlayer.EndOfMedia:
            if self.mode == "单曲" and self.player:
                self.player.setPosition(0)
                self.player.play()
            else:
                self.step(1)

    # ---------------- 下载 ----------------
    def download_song(self, song):
        idx = self.cmb_quality.currentIndex()
        _, fmt, br = QUALITIES[idx]
        r = self.tbl3.rowCount()
        self.tbl3.insertRow(r)
        it = QTableWidgetItem(song["name"])
        it.setIcon(QIcon(UK.icon_pixmap("download", 22, T["accent"],
                                        self.devicePixelRatioF())))
        self.tbl3.setItem(r, 0, it)
        self.tbl3.setItem(r, 1, QTableWidgetItem(song["artist"]))
        self.tbl3.setItem(r, 2, QTableWidgetItem(QUALITIES[idx][0]))
        self.tbl3.setItem(r, 3, QTableWidgetItem("准备中…"))
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(0)
        bar.setFixedHeight(10)
        holder = QWidget()
        hl = QHBoxLayout(holder)
        hl.setContentsMargins(6, 10, 6, 10)
        hl.addWidget(bar)
        self.tbl3.setCellWidget(r, 4, holder)
        self.tbl3.setRowHeight(r, 34)
        self.dl_rows[song["rid"]] = (r, bar)
        self.stack_holder4.setCurrentIndex(1)
        self.toast.show_msg("开始下载：%s" % song["name"])
        self.engine.download(song, fmt, br, self.chk_lyric.isChecked())

    @Slot(str, int)
    def on_progress(self, rid, pct):
        if rid in self.dl_rows:
            r, bar = self.dl_rows[rid]
            try:
                bar.setValue(pct)
                self.tbl3.setItem(r, 3, QTableWidgetItem("下载中 %d%%" % pct))
            except Exception:
                pass

    def on_downloaded(self, res):
        rid = res["song"]["rid"]
        if rid in self.dl_rows:
            r, bar = self.dl_rows[rid]
            try:
                self.tbl3.setItem(r, 3, QTableWidgetItem("✓ 完成 %.1f MB" % (res["size"] / 1048576)))
                self.tbl3.removeCellWidget(r, 4)          # 移除进度条控件，避免盖住文本
                self.tbl3.setItem(r, 4, QTableWidgetItem(""))
            except Exception:
                pass
        self.reload_local()
        self.toast.show_msg("已保存：%s" % os.path.basename(res["path"]), 3200)

    def on_size(self, rid, sz, fmt):
        for r in range(self.tbl.rowCount()):
            if r < len(self.songs) and self.songs[r]["rid"] == rid:
                txt = ("%s %.1f MB" % (fmt, sz / 1048576)) if sz else "不可用"
                if self.songs[r].get("pay"):
                    txt = "VIP · " + txt
                self.tbl.setItem(r, 4, QTableWidgetItem(txt))
                break

    def tbl_menu(self, pos):
        r = self.tbl.rowAt(pos.y())
        if r < 0 or r >= len(self.songs):
            return
        s = self.songs[r]
        m = QMenu(self)
        m.addAction("试听", lambda: self.play_row(r))
        m.addAction("下载（当前音质）", lambda: self.download_song(s))
        m.addAction("检测可用大小", lambda: self.engine.probe(
            s, *QUALITIES[self.cmb_quality.currentIndex()][1:]))
        m.addAction("加入播放队列", lambda: self.enqueue(s))
        m.exec(self.tbl.viewport().mapToGlobal(pos))

    def enqueue(self, song):
        self.queue.append({"song": song, "url": None})
        self.toast.show_msg("已加入队列（共 %d 首）" % len(self.queue))

    # ---------------- 本地曲库 ----------------
    def reload_local(self):
        d = self.ed_dir.text() if hasattr(self, "ed_dir") else K.OUTDIR
        K.OUTDIR = d or K.OUTDIR
        files = []
        for root, _dirs, names in os.walk(K.OUTDIR):
            for n in names:
                if n.lower().endswith((".mp3", ".flac", ".m4a", ".aac", ".wav", ".ogg")):
                    files.append(os.path.join(root, n))
        files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        self.local = files
        self._update_cache_label()
        if not hasattr(self, "tbl2"):
            return
        self.tbl2.setRowCount(0)
        for i, p in enumerate(files, 1):
            base = os.path.basename(p)
            name = base.rsplit(".", 1)[0]
            artist = ""
            m = re.match(r"(.+?) - (.+?) \[(\d+)\]", name)
            if m:
                name, artist = m.group(1), m.group(2)
            r = self.tbl2.rowCount()
            self.tbl2.insertRow(r)
            self.tbl2.setItem(r, 0, QTableWidgetItem(str(i)))
            it = QTableWidgetItem(name)
            it.setIcon(QIcon(UK.icon_pixmap("note", 26, T["accent"] if p.endswith(".flac")
                                            else T["muted"], self.devicePixelRatioF())))
            self.tbl2.setItem(r, 1, it)
            self.tbl2.setItem(r, 2, QTableWidgetItem(artist))
            self.tbl2.setItem(r, 3, QTableWidgetItem("%.1f MB" % (os.path.getsize(p) / 1048576)))
            self.tbl2.setRowHeight(r, 34)
        self.lbl_dir.setText("目录：%s   （%d 首）" % (os.path.abspath(K.OUTDIR), len(files)))
        self.stack_holder2.setCurrentIndex(1 if files else 0)

    def tbl2_menu(self, pos):
        r = self.tbl2.rowAt(pos.y())
        if r < 0 or r >= len(self.local):
            return
        p = self.local[r]
        m = QMenu(self)
        m.addAction("播放", lambda: self.play_local(r))
        m.addAction("在资源管理器中显示",
                    lambda: os.system('explorer /select,"%s"' % os.path.abspath(p)))
        m.addSeparator()
        m.addAction("删除文件", lambda: self.delete_local(p))
        m.exec(self.tbl2.viewport().mapToGlobal(pos))

    def delete_local(self, p):
        if QMessageBox.question(self, "删除", "删除文件？\n%s" % os.path.basename(p)) \
                == QMessageBox.Yes:
            try:
                os.remove(p)
                lrc = p.rsplit(".", 1)[0] + ".lrc"
                if os.path.exists(lrc):
                    os.remove(lrc)
                self.toast.show_msg("已删除：%s" % os.path.basename(p))
            except Exception as e:
                self.toast.show_msg("删除失败：%s" % str(e)[:60])
            self.reload_local()

    # ---------------- 歌词 ----------------
    def on_lyric(self, rid, txt):
        self.lyric_data = lrc_lines(txt)
        self.lyrics_view.set_lyrics(self.lyric_data)
        if self.player:
            self.lyrics_view.set_position(self.player.position())
        if not self.lyric_data:
            self.lbl_lyric_hint.setText("该曲暂无歌词")

    def tick_lyric(self):
        if self.lyric_data and self.player:
            self.lyrics_view.set_position(self.player.position())

    # ---------------- 杂项 ----------------
    def pick_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择下载目录", self.ed_dir.text())
        if d:
            self.ed_dir.setText(d)
            K.OUTDIR = d
            self.reload_local()
            self.toast.show_msg("下载目录：%s" % d)

    def open_dir(self):
        os.makedirs(K.OUTDIR, exist_ok=True)
        os.startfile(os.path.abspath(K.OUTDIR))       # noqa

    # ---------------- 缓存 ----------------
    def _cache_stat(self):
        lyr = getattr(K, "LYRIC_CACHE", "")
        n_l = len([f for f in os.listdir(lyr) if f.endswith(".lrc")]) if lyr and \
            os.path.isdir(lyr) else 0
        n_c = len(self.covers)
        return n_l, n_c

    def _update_cache_label(self):
        if not hasattr(self, "lbl_cache"):
            return
        n_l, n_c = self._cache_stat()
        self.lbl_cache.setText("歌词缓存 %d 首　·　封面缓存 %d 张　·　本地曲库 %d 首"
                               % (n_l, n_c, len(self.local)))

    def clear_cache(self):
        lyr = getattr(K, "LYRIC_CACHE", "")
        n = 0
        if lyr and os.path.isdir(lyr):
            for f in os.listdir(lyr):
                if f.endswith(".lrc"):
                    try:
                        os.remove(os.path.join(lyr, f))
                        n += 1
                    except Exception:
                        pass
        self._update_cache_label()
        self.toast.show_msg("已清空 %d 个歌词缓存" % n)

    def clear_covers(self):
        n = len(self.covers)
        self.covers.clear()
        self._update_cache_label()
        self.toast.show_msg("已清空 %d 张封面缓存（重新搜索即可再次加载）" % n)

    # ---------------- 播放行标记 ----------------
    def _mark_playing_row(self):
        cur_rid = (self.cur_song or {}).get("rid")
        for r in range(self.tbl.rowCount()):
            if r >= len(self.songs):
                break
            item = self.tbl.item(r, 0)
            if not item:
                continue
            on = (self.songs[r].get("rid") == cur_rid)
            f = item.font()
            f.setBold(on)
            item.setFont(f)
            item.setForeground(QColor(T["accent2"] if on else T["text"]))
            if on:
                self.tbl.setCurrentCell(r, 0)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self.toast.isVisible():
            self.toast.move(self.width() - self.toast.width() - 26,
                            self.height() - self.toast.height() - 120)
        self.spinner.move(self.width() - 60, 26)

    def closeEvent(self, e):
        self.save_cfg()
        super().closeEvent(e)


def res_path(name):
    base = getattr(sys, "_MEIPASS", HERE)
    return os.path.join(base, name)


def main():
    if "--selftest" in sys.argv:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    icon_file = res_path("appicon.ico")
    if os.path.exists(icon_file):
        app.setWindowIcon(QIcon(icon_file))
    app.setStyleSheet(QSS)
    w = Studio()
    if os.path.exists(icon_file):
        w.setWindowIcon(QIcon(icon_file))
    w.show()
    print("UI 构建成功：%dx%d，页面 %d 个" % (w.width(), w.height(), w.stack.count()))
    if "--selftest" in sys.argv:
        QTimer.singleShot(220, app.quit)
    app.exec()
    return 0


if __name__ == "__main__":
    sys.exit(main())
