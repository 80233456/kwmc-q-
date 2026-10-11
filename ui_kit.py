#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ui_kit.py — 界面组件库（矢量图标 / 图标按钮 / 动画歌词 / 指示动效 / 空状态 / Toast）

设计要点（举一反三）：
  * 图标全部用 QPainter 矢量绘制，不依赖 emoji 或字体 —— 任何机器上都不会缺字、不会错位；
    支持任意尺寸、任意颜色、状态色（常规/悬停/激活/禁用），并按设备像素比渲染保证高清屏锐利。
  * 控件动画统一用 QTimer(60fps) + 缓动插值，避免 Qt 属性动画在不同平台的表现差异。
  * 颜色统一从 THEME 取，改主题只需改一处。
"""
import math

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (QBrush, QColor, QFont, QFontMetrics, QIcon, QLinearGradient,
                           QPainter, QPainterPath, QPen, QPixmap, QRadialGradient)
from PySide6.QtWidgets import QWidget

# --------------------------------------------------------------------------- #
#  主题
# --------------------------------------------------------------------------- #
THEME = {
    "bg": "#0f1115",
    "panel": "#14171d",
    "card": "#171a21",
    "hover": "#1c202a",
    "line": "#232733",
    "text": "#e6e8ee",
    "muted": "#8b93a7",
    "dim": "#5d6577",
    "accent": "#6c5ce7",
    "accent2": "#00b894",
    "warn": "#ffb020",
    "danger": "#ff5d5d",
}


def accent_gradient(rect, horizontal=True):
    g = QLinearGradient(rect.topLeft(), rect.topRight() if horizontal
                        else rect.bottomLeft())
    g.setColorAt(0.0, QColor(THEME["accent"]))
    g.setColorAt(1.0, QColor(THEME["accent2"]))
    return g


# --------------------------------------------------------------------------- #
#  矢量图标
# --------------------------------------------------------------------------- #
def _p_path(p: QPainter, name: str, s: float):
    """在 s×s 的画布上绘制图标路径（线宽已按比例设好）。"""
    if name == "search":
        p.drawEllipse(QPointF(s * 0.43, s * 0.43), s * 0.26, s * 0.26)
        p.drawLine(QPointF(s * 0.63, s * 0.63), QPointF(s * 0.84, s * 0.84))
    elif name == "library":
        # 曲库：卡片 + 播放三角，语义明确且与"队列"区分
        p.drawRoundedRect(QRectF(s * 0.16, s * 0.22, s * 0.68, s * 0.56), s * 0.10, s * 0.10)
        path = QPainterPath()
        path.moveTo(s * 0.42, s * 0.38)
        path.lineTo(s * 0.64, s * 0.50)
        path.lineTo(s * 0.42, s * 0.62)
        path.closeSubpath()
        p.setBrush(QBrush(p.pen().color()))
        p.drawPath(path)
        p.setBrush(Qt.NoBrush)
    elif name == "download":
        p.drawLine(QPointF(s * 0.5, s * 0.16), QPointF(s * 0.5, s * 0.62))
        p.drawPolyline([QPointF(s * 0.3, s * 0.44), QPointF(s * 0.5, s * 0.66),
                        QPointF(s * 0.7, s * 0.44)])
        p.drawLine(QPointF(s * 0.2, s * 0.82), QPointF(s * 0.8, s * 0.82))
    elif name == "settings":
        # 推杆（sliders）：现代、明确，不像太阳
        for i, y in enumerate((0.30, 0.52, 0.74)):
            p.drawLine(QPointF(s * 0.16, s * y), QPointF(s * 0.84, s * y))
            cx = (0.36, 0.66, 0.46)[i]
            p.drawEllipse(QPointF(s * cx, s * y), s * 0.085, s * 0.085)
    elif name == "play":
        path = QPainterPath()
        path.moveTo(s * 0.30, s * 0.18)
        path.lineTo(s * 0.80, s * 0.50)
        path.lineTo(s * 0.30, s * 0.82)
        path.closeSubpath()
        p.drawPath(path)
    elif name == "pause":
        p.drawLine(QPointF(s * 0.36, s * 0.20), QPointF(s * 0.36, s * 0.80))
        p.drawLine(QPointF(s * 0.64, s * 0.20), QPointF(s * 0.64, s * 0.80))
    elif name == "stop":
        p.drawRect(QRectF(s * 0.28, s * 0.28, s * 0.44, s * 0.44))
    elif name == "prev":
        p.drawLine(QPointF(s * 0.26, s * 0.24), QPointF(s * 0.26, s * 0.76))
        path = QPainterPath()
        path.moveTo(s * 0.78, s * 0.24)
        path.lineTo(s * 0.36, s * 0.50)
        path.lineTo(s * 0.78, s * 0.76)
        path.closeSubpath()
        p.drawPath(path)
    elif name == "next":
        p.drawLine(QPointF(s * 0.74, s * 0.24), QPointF(s * 0.74, s * 0.76))
        path = QPainterPath()
        path.moveTo(s * 0.22, s * 0.24)
        path.lineTo(s * 0.64, s * 0.50)
        path.lineTo(s * 0.22, s * 0.76)
        path.closeSubpath()
        p.drawPath(path)
    elif name == "volume":
        path = QPainterPath()
        path.moveTo(s * 0.16, s * 0.40)
        path.lineTo(s * 0.32, s * 0.40)
        path.lineTo(s * 0.50, s * 0.22)
        path.lineTo(s * 0.50, s * 0.78)
        path.lineTo(s * 0.32, s * 0.60)
        path.lineTo(s * 0.16, s * 0.60)
        path.closeSubpath()
        p.drawPath(path)
        p.drawArc(QRectF(s * 0.44, s * 0.30, s * 0.36, s * 0.40), -60 * 16, 120 * 16)
    elif name == "mute":
        path = QPainterPath()
        path.moveTo(s * 0.16, s * 0.40)
        path.lineTo(s * 0.32, s * 0.40)
        path.lineTo(s * 0.50, s * 0.22)
        path.lineTo(s * 0.50, s * 0.78)
        path.lineTo(s * 0.32, s * 0.60)
        path.lineTo(s * 0.16, s * 0.60)
        path.closeSubpath()
        p.drawPath(path)
        p.drawLine(QPointF(s * 0.62, s * 0.36), QPointF(s * 0.86, s * 0.64))
        p.drawLine(QPointF(s * 0.86, s * 0.36), QPointF(s * 0.62, s * 0.64))
    elif name == "lyric":
        # 对白气泡 + 文字行：与"队列"图标明确区分
        path = QPainterPath()
        path.moveTo(s * 0.16, s * 0.24)
        path.lineTo(s * 0.84, s * 0.24)
        path.lineTo(s * 0.84, s * 0.66)
        path.lineTo(s * 0.50, s * 0.66)
        path.lineTo(s * 0.34, s * 0.82)
        path.lineTo(s * 0.34, s * 0.66)
        path.lineTo(s * 0.16, s * 0.66)
        path.closeSubpath()
        p.drawPath(path)
        p.drawLine(QPointF(s * 0.28, s * 0.38), QPointF(s * 0.72, s * 0.38))
        p.drawLine(QPointF(s * 0.28, s * 0.52), QPointF(s * 0.60, s * 0.52))
    elif name == "folder":
        path = QPainterPath()
        path.moveTo(s * 0.14, s * 0.28)
        path.lineTo(s * 0.42, s * 0.28)
        path.lineTo(s * 0.50, s * 0.38)
        path.lineTo(s * 0.86, s * 0.38)
        path.lineTo(s * 0.86, s * 0.78)
        path.lineTo(s * 0.14, s * 0.78)
        path.closeSubpath()
        p.drawPath(path)
    elif name == "refresh":
        p.drawArc(QRectF(s * 0.22, s * 0.22, s * 0.56, s * 0.56), 40 * 16, 280 * 16)
        p.drawPolyline([QPointF(s * 0.70, s * 0.18), QPointF(s * 0.80, s * 0.34),
                        QPointF(s * 0.62, s * 0.34)])
    elif name == "trash":
        p.drawLine(QPointF(s * 0.18, s * 0.28), QPointF(s * 0.82, s * 0.28))
        p.drawPolyline([QPointF(s * 0.28, s * 0.28), QPointF(s * 0.32, s * 0.82),
                        QPointF(s * 0.68, s * 0.82), QPointF(s * 0.72, s * 0.28)])
        p.drawLine(QPointF(s * 0.40, s * 0.20), QPointF(s * 0.60, s * 0.20))
    elif name == "queue":
        for i, y in enumerate((0.28, 0.46, 0.64, 0.82)):
            p.drawLine(QPointF(s * 0.24, s * y), QPointF(s * 0.78, s * y))
            p.drawPoint(QPointF(s * 0.14, s * y))
    elif name == "note":
        p.drawEllipse(QPointF(s * 0.34, s * 0.72), s * 0.15, s * 0.12)
        p.drawLine(QPointF(s * 0.49, s * 0.72), QPointF(s * 0.49, s * 0.22))
        p.drawPolyline([QPointF(s * 0.49, s * 0.24), QPointF(s * 0.82, s * 0.34),
                        QPointF(s * 0.82, s * 0.48), QPointF(s * 0.49, s * 0.38)])
    elif name == "shuffle":
        p.drawPolyline([QPointF(s * 0.16, s * 0.30), QPointF(s * 0.44, s * 0.30),
                        QPointF(s * 0.66, s * 0.70), QPointF(s * 0.84, s * 0.70)])
        p.drawPolyline([QPointF(s * 0.16, s * 0.70), QPointF(s * 0.44, s * 0.70),
                        QPointF(s * 0.60, s * 0.44)])
        p.drawPolyline([QPointF(s * 0.74, s * 0.22), QPointF(s * 0.86, s * 0.30),
                        QPointF(s * 0.74, s * 0.38)])
    elif name == "repeat":
        p.drawArc(QRectF(s * 0.18, s * 0.22, s * 0.64, s * 0.56), 30 * 16, 300 * 16)
        p.drawPolyline([QPointF(s * 0.62, s * 0.16), QPointF(s * 0.74, s * 0.30),
                        QPointF(s * 0.56, s * 0.34)])
    elif name == "repeat1":
        p.drawArc(QRectF(s * 0.18, s * 0.22, s * 0.64, s * 0.56), 30 * 16, 300 * 16)
        p.drawPolyline([QPointF(s * 0.62, s * 0.16), QPointF(s * 0.74, s * 0.30),
                        QPointF(s * 0.56, s * 0.34)])
        p.drawLine(QPointF(s * 0.50, s * 0.42), QPointF(s * 0.50, s * 0.58))
    elif name == "check":
        p.drawPolyline([QPointF(s * 0.22, s * 0.52), QPointF(s * 0.42, s * 0.72),
                        QPointF(s * 0.80, s * 0.30)])
    elif name == "close":
        p.drawLine(QPointF(s * 0.28, s * 0.28), QPointF(s * 0.72, s * 0.72))
        p.drawLine(QPointF(s * 0.72, s * 0.28), QPointF(s * 0.28, s * 0.72))
    elif name == "external":
        p.drawRect(QRectF(s * 0.22, s * 0.34, s * 0.44, s * 0.44))
        p.drawPolyline([QPointF(s * 0.50, s * 0.50), QPointF(s * 0.82, s * 0.18)])
        p.drawPolyline([QPointF(s * 0.62, s * 0.18), QPointF(s * 0.82, s * 0.18),
                        QPointF(s * 0.82, s * 0.38)])
    elif name == "heart":
        path = QPainterPath()
        path.moveTo(s * 0.5, s * 0.78)
        path.cubicTo(s * 0.05, s * 0.50, s * 0.18, s * 0.16, s * 0.5, s * 0.34)
        path.cubicTo(s * 0.82, s * 0.16, s * 0.95, s * 0.50, s * 0.5, s * 0.78)
        p.drawPath(path)
    elif name == "vip":
        path = QPainterPath()
        path.moveTo(s * 0.24, s * 0.30)
        path.lineTo(s * 0.38, s * 0.62)
        path.lineTo(s * 0.5, s * 0.36)
        path.lineTo(s * 0.62, s * 0.62)
        path.lineTo(s * 0.76, s * 0.30)
        path.lineTo(s * 0.68, s * 0.74)
        path.lineTo(s * 0.32, s * 0.74)
        path.closeSubpath()
        p.drawPath(path)
    elif name == "spinner":
        p.drawArc(QRectF(s * 0.18, s * 0.18, s * 0.64, s * 0.64), 30 * 16, 260 * 16)
    elif name == "warning":
        path = QPainterPath()
        path.moveTo(s * 0.5, s * 0.16)
        path.lineTo(s * 0.92, s * 0.84)
        path.lineTo(s * 0.08, s * 0.84)
        path.closeSubpath()
        p.drawPath(path)
        p.drawLine(QPointF(s * 0.5, s * 0.42), QPointF(s * 0.5, s * 0.62))
        p.drawPoint(QPointF(s * 0.5, s * 0.72))


FILLED = {"play", "prev", "next", "stop", "volume", "mute", "folder", "heart",
          "vip", "warning", "note"}


def icon_pixmap(name, size=20, color=None, dpr=1.0):
    """把矢量图标画成 QPixmap（按 dpr 渲染，高清屏不虚）。"""
    color = color or THEME["text"]
    px = QPixmap(int(size * dpr), int(size * dpr))
    px.setDevicePixelRatio(dpr)
    px.fill(Qt.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setRenderHint(QPainter.SmoothPixmapTransform, True)
    s = size
    pen = QPen(QColor(color))
    pen.setWidthF(max(1.6, s * 0.095))
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    if name in FILLED:
        p.setBrush(QBrush(QColor(color)))
    else:
        p.setBrush(Qt.NoBrush)
    p.translate(0, 0)
    _p_path(p, name, s)
    p.end()
    return px


def icon(name, size=20, color=None):
    return QIcon(icon_pixmap(name, size, color))


# --------------------------------------------------------------------------- #
#  图标按钮
# --------------------------------------------------------------------------- #
class IconButton(QWidget):
    """圆形/方角图标按钮：悬停底色、按下反馈、可选激活态，全部矢量绘制。"""

    clicked = Signal()

    def __init__(self, name, size=34, icon_size=18, color=None, active_color=None,
                 tooltip="", round_=True, parent=None):
        super().__init__(parent)
        self.name = name
        self.icon_size = icon_size
        self.color = color or THEME["text"]
        self.active_color = active_color or THEME["accent"]
        self.round_ = round_
        self._hover = False
        self._press = False
        self.active = False
        self._bg = 0.0            # 悬停底色渐入
        self.setFixedSize(size, size)
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)
        if tooltip:
            self.setToolTip(tooltip)
        self._t = QTimer(self)
        self._t.timeout.connect(self._anim)
        self._t.start(16)

    def set_active(self, on):
        self.active = bool(on)
        self.update()

    def set_icon(self, name):
        self.name = name
        self.update()

    def _anim(self):
        target = 1.0 if (self._hover or self._press) else 0.0
        if abs(self._bg - target) > 0.01:
            self._bg += (target - self._bg) * 0.28
            self.update()

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self._press = False
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._press = True
            self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self._press:
            self._press = False
            self.update()
            if self.rect().contains(e.position().toPoint()):
                self.clicked.emit()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        col = self.active_color if self.active else self.color
        if self.active:
            g = accent_gradient(r)
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(g))
            p.drawRoundedRect(r, r.height() * 0.5 if self.round_ else 8,
                              r.height() * 0.5 if self.round_ else 8)
        elif self._bg > 0.01:
            c = QColor(THEME["hover"])
            c.setAlphaF(min(1.0, 0.35 + 0.65 * self._bg))
            p.setPen(Qt.NoPen)
            p.setBrush(c)
            p.drawRoundedRect(r, r.height() * 0.5 if self.round_ else 8,
                              r.height() * 0.5 if self.round_ else 8)
        dpr = self.devicePixelRatioF()
        pm = icon_pixmap(self.name, self.icon_size,
                         "#ffffff" if self.active else col, dpr)
        pm.setDevicePixelRatio(dpr)
        x = (self.width() - self.icon_size) / 2
        y = (self.height() - self.icon_size) / 2
        p.drawPixmap(int(x), int(y), pm)
        p.end()


# --------------------------------------------------------------------------- #
#  播放中律动指示（三根跳动的竖条）
# --------------------------------------------------------------------------- #
class Spinner(QWidget):
    """旋转加载指示（矢量弧线 + 60fps 旋转，避免"静止的弧"）。"""

    def __init__(self, size=22, color=None, parent=None):
        super().__init__(parent)
        self.color = color or THEME["accent"]
        self.setFixedSize(size, size)
        self._angle = 0
        self._t = QTimer(self)
        self._t.timeout.connect(self._tick)
        self._t.start(16)

    def _tick(self):
        self._angle = (self._angle + 7) % 360
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = QRectF(2, 2, self.width() - 4, self.height() - 4)
        # 底环
        pen = QPen(QColor(255, 255, 255, 28))
        pen.setWidthF(2.6)
        p.setPen(pen)
        p.drawEllipse(r)
        # 旋转弧
        pen.setColor(QColor(self.color))
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.drawArc(r, int(self._angle * 16), int(100 * 16))
        p.end()


class EqBars(QWidget):
    def __init__(self, parent=None, color=None, bars=3):
        super().__init__(parent)
        self.color = color or THEME["accent2"]
        self.bars = bars
        self.phase = 0.0
        self.playing = True
        self.setFixedSize(bars * 5 + 2, 16)
        self._t = QTimer(self)
        self._t.timeout.connect(self._tick)
        self._t.start(60)

    def set_playing(self, on):
        self.playing = on
        self.update()

    def _tick(self):
        if self.playing:
            self.phase += 0.28
            self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(Qt.NoPen)
        c = QColor(self.color)
        for i in range(self.bars):
            h = (0.35 + 0.65 * abs(math.sin(self.phase + i * 0.9))) * (self.height() - 2)
            p.setBrush(c)
            p.drawRoundedRect(QRectF(1 + i * 5, self.height() - h, 3, h), 1.5, 1.5)
        p.end()


# --------------------------------------------------------------------------- #
#  空状态
# --------------------------------------------------------------------------- #
class EmptyState(QWidget):
    def __init__(self, icon_name="search", title="", hint="", parent=None):
        super().__init__(parent)
        self.icon_name = icon_name
        self.title = title
        self.hint = hint

    def set_text(self, title, hint="", icon_name=None):
        self.title, self.hint = title, hint
        if icon_name:
            self.icon_name = icon_name
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        cx, cy = self.width() / 2, self.height() / 2
        pm = icon_pixmap(self.icon_name, 54, THEME["dim"], self.devicePixelRatioF())
        p.setOpacity(0.55)
        p.drawPixmap(int(cx - 27), int(cy - 74), pm)
        p.setOpacity(1.0)
        f = QFont("Microsoft YaHei UI", 12)
        f.setBold(True)
        p.setFont(f)
        p.setPen(QColor(THEME["muted"]))
        p.drawText(QRectF(0, cy - 6, self.width(), 30), Qt.AlignHCenter, self.title)
        p.setFont(QFont("Microsoft YaHei UI", 9))
        p.setPen(QColor(THEME["dim"]))
        p.drawText(QRectF(0, cy + 24, self.width(), 60), Qt.AlignHCenter | Qt.TextWordWrap,
                   self.hint)
        p.end()


# --------------------------------------------------------------------------- #
#  动画歌词视图（核心）
# --------------------------------------------------------------------------- #
class LyricsView(QWidget):
    """
    自绘歌词：平滑滚动 + 逐行淡入 + 当前行卡拉OK式渐变填充 + 点击跳转。

    * 每帧(60fps)按缓动把滚动偏移趋向目标行，避免"跳变"；
    * 当前行文字用两遍绘制：底色（暗）+ 按进度裁剪的高亮色 → 平滑"唱到哪亮到哪"；
    * 非当前行按距离做透明度衰减，视觉层次清晰；
    * 点击任意行 → 发出 seekRequested(毫秒)。
    """
    seekRequested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.lines = []            # [(ms, text)]
        self.pos = 0
        self.active = -1
        self._offset = 0.0         # 当前滚动偏移（行单位）
        self._target = 0.0
        self._frac = 0.0           # 当前行填充比例
        self._pop = 1.0            # 切行时的"弹入"进度
        self._hover_line = -1
        self.setMinimumHeight(240)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_OpaquePaintEvent, False)
        self._t = QTimer(self)
        self._t.timeout.connect(self._tick)
        self._t.start(16)

    # ---- 数据 ----
    def set_lyrics(self, lines):
        # 过滤空白行：否则"激活行是空行"时会出现只有一个指示条、看不到文字的情况
        self.lines = [(ms, t) for ms, t in (lines or []) if (t or "").strip()]
        self.active = -1
        self._offset = self._target = 0.0
        self._pop = 1.0
        self.update()

    def set_position(self, ms):
        if not self.lines:
            return
        self.pos = ms
        idx = 0
        for i, (t, _s) in enumerate(self.lines):
            if t <= ms:
                idx = i
            else:
                break
        if idx != self.active:
            self.active = idx
            self._target = float(idx)
            self._pop = 0.0                     # 新行弹入动画
        # 当前行填充比例（用于卡拉OK渐变）
        if 0 <= idx < len(self.lines):
            t0 = self.lines[idx][0]
            t1 = self.lines[idx + 1][0] if idx + 1 < len(self.lines) else t0 + 4000
            span = max(1, t1 - t0)
            self._frac = min(1.0, max(0.0, (ms - t0) / span))

    # ---- 动画 ----
    def _tick(self):
        need = False
        d = self._target - self._offset
        if abs(d) > 0.002:
            self._offset += d * 0.18          # 缓动系数：小=更顺滑，大=更跟手
            need = True
        if self._pop < 1.0:
            self._pop = min(1.0, self._pop + 0.09)
            need = True
        if need:
            self.update()

    # ---- 布局参数 ----
    def _metrics(self):
        fm = QFontMetrics(self._font_active())
        lh = max(34, fm.height() + 18)
        return lh

    def _font_active(self):
        f = QFont("Microsoft YaHei UI", 14)
        f.setBold(True)
        return f

    def _font_normal(self):
        return QFont("Microsoft YaHei UI", 11)

    # ---- 绘制 ----
    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.TextAntialiasing, True)
        W, H = self.width(), self.height()
        # 自绘背景（组件必须自己铺底色，避免露出上位白色）
        bg = QColor(THEME["panel"])
        if self.parent() is None or not isinstance(self.parent(), QWidget):
            bg = QColor(THEME["bg"])
        p.fillRect(self.rect(), bg)
        if not self.lines:
            p.setPen(QColor(THEME["dim"]))
            p.setFont(QFont("Microsoft YaHei UI", 11))
            p.drawText(self.rect(), Qt.AlignCenter, "暂无歌词")
            p.end()
            return
        lh = self._metrics()
        mid = H * 0.42
        f_n, f_a = self._font_normal(), self._font_active()
        for i, (ms, text) in enumerate(self.lines):
            y = mid + (i - self._offset) * lh
            if y < -lh or y > H + lh:
                continue
            dist = abs(i - self._offset)
            if dist > 6:
                continue
            alpha = max(0.0, 1.0 - dist / 6.0)
            if i == self.active:
                # 激活行：柔和药丸底 + 暗色文字 + 按进度裁剪的高亮（卡拉OK）
                fm_a = QFontMetrics(f_a)
                tw = fm_a.horizontalAdvance(text)
                pill = QRectF((W - tw) / 2 - 20, y - lh / 2 + 6, tw + 40, lh - 12)
                p.setPen(Qt.NoPen)
                pc = QColor(THEME["accent"])
                pc.setAlphaF(0.10 + 0.10 * self._pop)
                p.setBrush(pc)
                p.drawRoundedRect(pill, (lh - 12) / 2, (lh - 12) / 2)
                p.save()
                p.setFont(f_a)
                p.setPen(QColor(168, 176, 196, 190))
                rect = QRectF(0, y - lh / 2 + 8, W, lh)
                p.drawText(rect, Qt.AlignHCenter | Qt.AlignVCenter, text)
                clip_w = W * self._frac
                if clip_w > 1:
                    p.setClipRect(QRectF((W - clip_w) / 2, y - lh / 2, clip_w, lh))
                    grad = accent_gradient(QRectF(0, 0, W, 12), horizontal=True)
                    p.setPen(QPen(QBrush(grad), 1))
                    p.drawText(rect, Qt.AlignHCenter | Qt.AlignVCenter, text)
                p.restore()
            else:
                p.setFont(f_n)
                col = QColor(THEME["muted"] if dist < 2.2 else THEME["dim"])
                col.setAlphaF(min(1.0, alpha * (0.95 if dist < 2.2 else 0.75)))
                p.setPen(col)
                p.drawText(QRectF(0, y - lh / 2, W, lh), Qt.AlignHCenter | Qt.AlignVCenter, text)
            if i == self._hover_line and i != self.active:
                p.setPen(QPen(QColor(THEME["accent"]), 1, Qt.DashLine))
                p.drawLine(QPointF(W * 0.2, y + lh / 2 - 6), QPointF(W * 0.8, y + lh / 2 - 6))
        # 上下渐隐遮罩
        top = QLinearGradient(0, 0, 0, H)
        c0 = QColor(THEME["bg"])
        c0.setAlpha(235)
        c1 = QColor(THEME["bg"])
        c1.setAlpha(0)
        top.setColorAt(0.0, c0)
        top.setColorAt(0.22, c1)
        top.setColorAt(0.78, c1)
        top.setColorAt(1.0, c0)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(top))
        p.drawRect(self.rect())
        p.end()

    # ---- 交互 ----
    def _line_at(self, y):
        lh = self._metrics()
        mid = self.height() * 0.42
        return int(round((y - mid) / lh + self._offset))

    def mouseMoveEvent(self, e):
        i = self._line_at(e.position().y())
        self._hover_line = i if 0 <= i < len(self.lines) else -1
        self.setCursor(Qt.PointingHandCursor if self._hover_line >= 0 else Qt.ArrowCursor)
        self.update()

    def leaveEvent(self, _e):
        self._hover_line = -1
        self.update()

    def mousePressEvent(self, e):
        i = self._line_at(e.position().y())
        if 0 <= i < len(self.lines):
            self.seekRequested.emit(self.lines[i][0])
            self.active = i
            self._target = float(i)
