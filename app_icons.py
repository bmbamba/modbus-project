"""
app_icons.py  —  generates QIcon objects at runtime using QPainter.
No .ico files required. Works perfectly with PyInstaller.

Usage:
    from app_icons import server_icon, client_icon
    self.setWindowIcon(server_icon())   # in ServerWindow
    self.setWindowIcon(client_icon())   # in ClientWindow
"""

import math
from PySide6.QtGui   import QIcon, QPixmap, QPainter, QColor, QPen, QBrush, QPolygon
from PySide6.QtCore  import Qt, QPoint, QRect

# ── Colour palette ─────────────────────────────────────────────
BG         = QColor(  0,   0,   0,   0)   # transparent
DARK       = QColor( 30,  36,  48, 255)
BLUE       = QColor( 59, 130, 246, 255)
BLUE_LIGHT = QColor( 96, 165, 250, 255)
LINE_COL   = QColor( 59, 130, 246, 180)
WHITE      = QColor(241, 245, 249, 255)
SCREEN     = QColor( 45,  55,  72, 255)


def _make_pixmap(size: int, draw_fn) -> QPixmap:
    px = QPixmap(size, size)
    px.fill(BG)
    p = QPainter(px)
    p.setRenderHint(QPainter.Antialiasing)
    draw_fn(p, size)
    p.end()
    return px


def _draw_server(p: QPainter, s: int):
    """Central blue rounded-square connected to 4 satellite circles."""
    cx, cy = s // 2, s // 2

    # centre node
    cn = int(s * 0.22)
    cr = max(4, int(s * 0.06))
    p.setPen(QPen(BLUE_LIGHT, max(1, s // 64)))
    p.setBrush(QBrush(BLUE))
    p.drawRoundedRect(cx - cn, cy - cn, cn * 2, cn * 2, cr, cr)

    # satellite nodes
    sn  = int(s * 0.085)
    orb = int(s * 0.34)
    positions = [
        (cx,       cy - orb),
        (cx + orb, cy),
        (cx,       cy + orb),
        (cx - orb, cy),
    ]

    # connection lines
    lw = max(2, s // 80)
    p.setPen(QPen(LINE_COL, lw))
    for nx, ny in positions:
        dx, dy = nx - cx, ny - cy
        dist   = math.hypot(dx, dy)
        ux, uy = dx / dist, dy / dist
        gc     = cn + s * 0.03
        gn     = sn + s * 0.02
        p.drawLine(int(cx + ux * gc), int(cy + uy * gc),
                   int(nx - ux * gn), int(ny - uy * gn))

    # satellite circles
    for nx, ny in positions:
        p.setPen(QPen(BLUE_LIGHT, max(1, s // 80)))
        p.setBrush(QBrush(DARK))
        p.drawEllipse(QPoint(nx, ny), sn, sn)
        # inner dot
        dot = max(2, sn // 3)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(BLUE_LIGHT))
        p.drawEllipse(QPoint(nx, ny), dot, dot)

    # white centre dot
    wd = max(3, cn // 3)
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(WHITE))
    p.drawEllipse(QPoint(cx, cy), wd, wd)


def _draw_client(p: QPainter, s: int):
    """Client device → arrow → server rack."""
    cy    = s // 2
    r     = max(3, int(s * 0.045))
    sc_pad = max(2, s // 40)

    # ── Client device (left)
    cl_cx = int(s * 0.18)
    cl_w  = int(s * 0.20)
    cl_h  = int(s * 0.26)
    p.setPen(QPen(BLUE_LIGHT, max(1, s // 80)))
    p.setBrush(QBrush(DARK))
    p.drawRoundedRect(cl_cx - cl_w//2, cy - cl_h//2, cl_w, cl_h, r, r)

    # screen area
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(SCREEN))
    p.drawRoundedRect(cl_cx - cl_w//2 + sc_pad,
                      cy - cl_h//2 + sc_pad,
                      cl_w - sc_pad*2,
                      cl_h//4*3 - sc_pad,
                      max(1, r//2), max(1, r//2))

    # status dot
    p.setBrush(QBrush(BLUE))
    dot = max(2, s // 40)
    p.drawEllipse(QPoint(cl_cx, cy + cl_h//4 + sc_pad*2), dot, dot)

    # ── Server rack (right)
    sv_cx = int(s * 0.82)
    sv_w  = int(s * 0.16)
    sv_h  = int(s * 0.32)
    p.setPen(QPen(BLUE, max(2, s // 64)))
    p.setBrush(QBrush(DARK))
    p.drawRoundedRect(sv_cx - sv_w//2, cy - sv_h//2, sv_w, sv_h, r, r)

    # rack slot lines
    slot_gap = sv_h // 5
    p.setPen(QPen(BLUE_LIGHT, max(1, s // 128)))
    for k in range(1, 4):
        sy = cy - sv_h//2 + slot_gap * k
        p.drawLine(sv_cx - sv_w//2 + sc_pad, sy,
                   sv_cx + sv_w//2 - sc_pad, sy)

    # LED dot on server
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(BLUE))
    led = max(2, s // 48)
    p.drawEllipse(QPoint(sv_cx - sv_w//2 + sc_pad*2,
                         cy - sv_h//2 + sc_pad*2), led, led)

    # ── Arrow
    gap     = int(s * 0.04)
    ax0     = cl_cx + cl_w//2 + gap
    ax1     = sv_cx - sv_w//2 - gap
    aw      = max(5, s // 24)   # arrowhead half-width
    al      = max(7, s // 20)   # arrowhead length
    lw      = max(2, s // 60)

    p.setPen(QPen(BLUE, lw))
    p.drawLine(ax0, cy, ax1 - al, cy)

    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(BLUE))
    tip = QPolygon([
        QPoint(ax1,      cy),
        QPoint(ax1 - al, cy - aw),
        QPoint(ax1 - al, cy + aw),
    ])
    p.drawPolygon(tip)


def server_icon() -> QIcon:
    icon = QIcon()
    for size in (16, 32, 48, 64, 128, 256):
        icon.addPixmap(_make_pixmap(size, _draw_server))
    return icon


def client_icon() -> QIcon:
    icon = QIcon()
    for size in (16, 32, 48, 64, 128, 256):
        icon.addPixmap(_make_pixmap(size, _draw_client))
    return icon
